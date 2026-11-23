"""From an estimate to something a homeowner can act on: a range, a verdict, and roughly what it means in taxes."""
from __future__ import annotations

import numpy as np
import pandas as pd

IN_LINE, CLOSER_LOOK, LIKELY_HIGH, LOW, NO_ESTIMATE = "in_line", "closer_look", "likely_high", "low", "no_estimate"

# Ohio's two property tax credits that most homeowners get, as a share of the tax after reduction factors.
# Rates vary by levy age; the county publishes each district's actual rates, which tax_rates() uses.


def band_table(resid_log: np.ndarray, spread: np.ndarray, bins: int = 4, q=(0.10, 0.90)) -> pd.DataFrame:
    """Residual quantiles (log of price / estimate) by how much a home's comps disagree, from homes whose sale
    the estimate didn't see. Returns bin edges on `spread` and the lower/upper quantiles for each bin."""
    ok = np.isfinite(resid_log) & np.isfinite(spread)
    edges = np.quantile(spread[ok], np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = 0.0, np.inf
    rows = []
    for i in range(bins):
        sel = ok & (spread >= edges[i]) & (spread < edges[i + 1])
        lo, hi = np.quantile(resid_log[sel], q)
        rows.append({"spread_lo": edges[i], "spread_hi": edges[i + 1], "q_lo": lo, "q_hi": hi, "n": int(sel.sum())})
    return pd.DataFrame(rows)


def apply_band(est_log: np.ndarray, spread: np.ndarray, table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    i = np.clip(np.searchsorted(table["spread_hi"].to_numpy(), np.nan_to_num(spread, nan=np.inf), side="right"), 0, len(table) - 1)
    return est_log + table["q_lo"].to_numpy()[i], est_log + table["q_hi"].to_numpy()[i]


def classify(value: np.ndarray, est: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """First version, kept for comparison: verdict by where the county's value falls in the likely range.
    Replaced by classify_chance, because the range alone over-flagged expensive homes."""
    v = np.asarray(value, float)
    out = np.full(len(v), NO_ESTIMATE, dtype=object)
    ok = np.isfinite(est)
    out[ok & (v > hi)] = LIKELY_HIGH
    out[ok & (v > est) & (v <= hi)] = CLOSER_LOOK
    out[ok & (v <= est) & (v >= lo)] = IN_LINE
    out[ok & (v < lo)] = LOW
    return out


# ── The verdict: how often homes like this one sold for less than their county value ─────────────────────────
# A logistic regression on 2026 sales (after the valuation date): P(sale price < county value) from
# - gap: log(county value / our estimate)
# - spread: how much the comps disagree
# - level: log of our estimate (centered), because the county values cheap and expensive homes a little differently
CENTER = 12.7  # about $330,000 in log dollars
LIKELY_HIGH_AT, CLOSER_LOOK_AT, LOW_BELOW = 0.4, 0.25, 0.1


def chance_design(gap: np.ndarray, spread: np.ndarray, est_log: np.ndarray) -> np.ndarray:
    lvl = est_log - CENTER
    return np.c_[np.ones(len(gap)), gap, gap * gap, spread, lvl, gap * spread, gap * lvl]


def fit_chance(gap: np.ndarray, spread: np.ndarray, est_log: np.ndarray, sold_below: np.ndarray, l2: float = 1e-3) -> np.ndarray:
    """Newton's method for a lightly ridge-penalized logistic regression."""
    ok = np.isfinite(gap) & np.isfinite(spread) & np.isfinite(est_log)
    X, y = chance_design(gap[ok], spread[ok], est_log[ok]), np.asarray(sold_below, float)[ok]
    b = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ b))
        H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(b))
        step = np.linalg.solve(H, X.T @ (y - p) - l2 * b)
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return b


def chance(coef: np.ndarray, gap: np.ndarray, spread: np.ndarray, est_log: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-chance_design(gap, spread, est_log) @ coef))


def classify_chance(p: np.ndarray, gap: np.ndarray) -> np.ndarray:
    """- likely_high: the county's value is above our estimate, and at least 4 in 10 homes like this sold for less
      (about 1.5 in 10 of all homes did, on screened 2026 sales)
    - closer_look: above our estimate, and at least 1 in 4 like it sold for less
    - low: below our estimate, and fewer than 1 in 10 like it sold for less (filing could invite a higher value)
    - in_line: everything else"""
    out = np.full(len(p), NO_ESTIMATE, dtype=object)
    ok = np.isfinite(p) & np.isfinite(gap)
    out[ok] = IN_LINE
    out[ok & (gap < 0) & (p < LOW_BELOW)] = LOW
    out[ok & (gap > 0) & (p >= CLOSER_LOOK_AT)] = CLOSER_LOOK
    out[ok & (gap > 0) & (p >= LIKELY_HIGH_AT)] = LIKELY_HIGH
    return out


def tax_rates(tax_parcels: pd.DataFrame, tax_detail: pd.DataFrame, homes: pd.DataFrame) -> pd.DataFrame:
    """Per tax district: dollars of 2025 tax per dollar of market value, before and after the two homeowner credits.

    AnnualSubtotal / (35% of 2025 market value) is the district's effective rate after HB 920 reduction factors.
    Those factors will adjust for the 2026 update, so the 2026 rate will be somewhat lower; we scale by the
    district's ratio of total 2025 to 2026 residential value, which is how the factors offset an across-the-board rise
    for voted levies (inside millage doesn't roll back, so this slightly understates)."""
    d = homes[["pid", "tax_district", "value_2025", "value_2026"]].merge(tax_detail, left_on="pid", right_on="PARCEL ID")
    d = d.merge(tax_parcels[["PARCEL ID", "NonBusinessRate", "OwnOccRate"]], on="PARCEL ID", how="left")
    d = d[(d["value_2025"] > 0) & (d["AnnualSubtotal"] > 0)]
    g = d.groupby("tax_district").agg(subtotal=("AnnualSubtotal", "sum"), v25=("value_2025", "sum"), v26=("value_2026", "sum"),
                                      nonbusiness=("NonBusinessRate", "median"), owner_occ=("OwnOccRate", "median"),
                                      homes=("pid", "size"))
    g["per_dollar_2025"] = g["subtotal"] / g["v25"]
    g["per_dollar_2026"] = g["per_dollar_2025"] * g["v25"] / g["v26"]
    g["credits"] = g["nonbusiness"].fillna(0) + g["owner_occ"].fillna(0)
    return g


def yearly_tax_difference(excess: np.ndarray, district: pd.Series, rates: pd.DataFrame) -> np.ndarray:
    """Rough yearly tax on `excess` dollars of value, for an owner-occupant, at estimated 2026 rates."""
    per = district.map(rates["per_dollar_2026"]).to_numpy(float)
    cred = district.map(rates["credits"]).fillna(0).to_numpy(float)
    return np.asarray(excess, float) * per * (1 - cred)
