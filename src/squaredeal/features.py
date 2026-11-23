"""Turn the county's raw codes into one row per home and one row per usable sale."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import VALUATION_DATE

SINGLE_FAMILY = {"510", "511"}  # single-family dwelling on a platted lot / on an unplatted lot
YEAR = pd.Timestamp(VALUATION_DATE).year

GRADE_BASE = {"E": 0.0, "D": 1.0, "C": 2.0, "B": 3.0, "A": 4.0, "X": 5.0}
CONDITION = {"Q": 0, "U": 0, "P": 1, "F": 2, "A": 3, "G": 4, "V": 5, "E": 6}
BASEMENT_SHARE = {"B": 1.0, "9": 0.75, "3": 0.75, "8": 0.5, "2": 0.5, "7": 0.25, "1": 0.25}

# Deeds that normally mean a market sale. Used only to screen 2026 sales the county hasn't validated yet.
MARKET_DEEDS = {"WD - (General) Warranty Deed", "SV - Survivorship Deed", "GW - General Warranty Deed (Legacy)",
                "LW - Limited or Special Warranty Deed"}


def grade_score(code: str | float) -> float:
    """'C - AVERAGE QUALITY' -> 2.0, 'C+1 - ...' -> 2.33, 'B-2 - ...' -> 2.33. Each +/- step is a third of a grade."""
    if not isinstance(code, str):
        return np.nan
    m = re.match(r"\s*([A-EX])([+-]\d)?", code)
    if not m:
        return np.nan
    return GRADE_BASE[m.group(1)] + (int(m.group(2)) / 3 if m.group(2) else 0.0)


def lead_code(code: str | float) -> str:
    """'B - FULL BASEMENT' -> 'B'."""
    return code.split(" - ")[0].strip() if isinstance(code, str) else ""


def street_key(direction, street, suffix, suffix2) -> str:
    parts = [p for p in (direction, street, suffix, suffix2) if isinstance(p, str) and p.strip()]
    return re.sub(r"\s+", " ", " ".join(parts).upper()).strip()


def homes(parcels: pd.DataFrame, dwellings: pd.DataFrame, values_2025: pd.Series, tax: pd.DataFrame,
          centroids: pd.DataFrame) -> pd.DataFrame:
    """One row per single-family home with the features the model uses. `modelable` marks homes we can estimate."""
    p = parcels[parcels["LUC"].isin(SINGLE_FAMILY)].copy()
    d = dwellings.copy()
    p = p.merge(d, on="PARCEL ID", how="left").merge(values_2025, left_on="PARCEL ID", right_index=True, how="left")
    p = p.merge(tax, on="PARCEL ID", how="left")
    p["pid10"] = p["PARCEL ID"].str[:10]
    p = p.merge(centroids, on="pid10", how="left")

    num = lambda c: pd.to_numeric(p[c], errors="coerce")
    out = pd.DataFrame({
        "pid": p["PARCEL ID"],
        "address": p["SiteAddress"].fillna("").str.strip(),
        "number": num("ADRNOLOW"),
        "street": [street_key(*r) for r in p[["ADRDIR", "ADRSTR", "ADRSUF", "ADRSUF2"]].itertuples(index=False)],
        # The county's ZipCode field is mostly blank; the site address ends with the ZIP.
        "zip": p["SiteAddress"].fillna("").str.extract(r"(\d{5})\s*$")[0].fillna(p["ZipCode"].fillna("").str[:5]),
        "school": p["SchoolDistrictDesc"].fillna(""),
        "tax_district": p["TaxDistrict"].fillna(""),
        "nbhd": p["NBHD"].fillna(""),
        "x": p["x"], "y": p["y"], "lat": p["lat"], "lon": p["lon"],
        "value_2025": p["value_2025"], "value_2026": p["value_2026"],
        "cards": p["cards"],
        "sqft": num("SFLA"),
        "year_built": num("YRBLT"),
        "eff_year": num("EFFYR"),
        "grade": p["GRADE"].map(grade_score),
        "condition": p["COND"].map(lead_code).map(CONDITION),
        "beds": num("RMBED"),
        "baths": num("FIXBATH").fillna(0) + 0.5 * num("FIXHALF").fillna(0),
        "basement": p["BSMT"].map(lead_code).map(BASEMENT_SHARE).fillna(0.0),
        "fin_basement": num("FINBSMTAREA").fillna(0),
        "stories": pd.to_numeric(p["STORIES"].map(lead_code), errors="coerce"),
        "central_air": (p["HEAT"].map(lead_code) == "2").astype(float),
        "style": p["STYLE"].map(lead_code),
        "grade_code": p["GRADE"].map(lead_code),
        "condition_word": p["COND"].fillna("").str.split(" - ").str[-1].str.title(),
        "acres": p["acres"].where(p["acres"] > 0, pd.to_numeric(p["gis_acres"], errors="coerce")),
    })
    out["age"] = (YEAR - out["year_built"]).clip(lower=0)
    # Effective age reflects remodeling; fall back to actual age when the county has none.
    out["eff_age"] = (YEAR - out["eff_year"]).where(out["eff_year"].notna(), out["age"]).clip(lower=0)
    out["modelable"] = (
        (out["cards"] == 1) & (out["sqft"] >= 400) & (out["sqft"] <= 10000) & out["grade"].notna()
        & out["condition"].notna() & out["value_2026"].gt(0) & out["x"].notna() & out["acres"].gt(0)
        & out["year_built"].between(1800, YEAR)
    )
    return out.reset_index(drop=True)


def usable_sales(sales: pd.DataFrame, homes: pd.DataFrame, transfers: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Single-parcel sales of modelable homes, labeled as comps (validated, 2023-2025) or holdout (2026, screened).

    2026 sales aren't validated yet. They're screened by deed type, then by a model of the county's own validity
    calls (screen.py) when transfer records are given. Returns the sales and a summary of the screening."""
    from . import screen

    s = sales[(sales["parcels_in_sale"] == 1) & sales["date"].notna() & sales["price"].notna()
              & (sales["SALETYPE"].fillna("") != "1 - LAND ONLY")]
    s = s.merge(homes.loc[homes["modelable"], ["pid", "grade", "condition", "eff_age", "value_2026"]],
                left_on="PARCEL ID", right_on="pid")
    validated = (s["VALID"] == "0 - VALID") & s["date"].between("2023-01-01", "2025-12-31") & (s["price"] >= 30000)
    deed_screen = s["INSTRUMENT"].isin(MARKET_DEEDS) & s["price"].between(50000, 5_000_000)
    pending = (s["VALID"] == "Y - WF FLAG") & (s["date"] >= VALUATION_DATE) & deed_screen
    summary = {"pending_2026_deed_screened": int(pending.sum())}
    s["p_valid"] = np.nan
    if transfers is not None:
        flags = screen.transfer_flags(transfers)
        s = s.merge(flags, on=["PARCEL ID", "date"], how="left")
        s["buyer_company"] = s["buyer_company"].fillna(False).astype(bool)
        s["seller_company"] = s["seller_company"].fillna(False).astype(bool)
        decided = deed_screen & s["date"].between("2023-01-01", "2025-12-31") & (s["VALID"] != "Y - WF FLAG")
        train = s[decided].assign(is_valid=(s.loc[decided, "VALID"] == "0 - VALID").astype(float))
        # Out-of-time check: fit on 2023-2024, score 2025.
        early, late = train[train["date"].dt.year < 2025], train[train["date"].dt.year == 2025]
        b_check = screen.fit(early)
        p_late = screen.predict(b_check, late)
        kept = p_late >= screen.KEEP_AT
        summary.update({
            "validity_model_auc_2025": round(screen.auc(late["is_valid"].to_numpy(), p_late), 4),
            "share_valid_2025_deed_screened": round(float(late["is_valid"].mean()), 4),
            "share_valid_2025_after_screen": round(float(late["is_valid"][kept].mean()), 4),
            "share_kept_2025": round(float(kept.mean()), 4),
        })
        b = screen.fit(train)
        s.loc[pending, "p_valid"] = screen.predict(b, s[pending])
        pending = pending & (s["p_valid"] >= screen.KEEP_AT)
    summary["pending_2026_kept"] = int(pending.sum())
    s = s[validated | pending].copy()
    s["set"] = np.where(validated.loc[s.index], "comps", "holdout")
    # The same home sold twice in a set: keep the latest sale.
    s = s.sort_values("date").drop_duplicates(["pid", "set"], keep="last")
    return s[["pid", "date", "price", "VALID", "INSTRUMENT", "p_valid", "set"]].reset_index(drop=True), summary
