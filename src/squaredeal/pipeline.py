"""The steps shared by build, validate, and export."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import VALUATION_DATE, comps, features, hedonic, load, timeindex, verdict

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def prepare(raw: Path = RAW, cache: Path = INTERIM, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Homes and usable sales, cached as parquet. Also returns tax tables for the tax estimate."""
    cache.mkdir(parents=True, exist_ok=True)
    paths = {k: cache / f"{k}.parquet" for k in ["homes", "sales", "rates"]}
    summary_path = cache / "screen.json"
    if not refresh and all(p.exists() for p in paths.values()) and summary_path.exists():
        return (pd.read_parquet(paths["homes"]), pd.read_parquet(paths["sales"]),
                {"rates": pd.read_parquet(paths["rates"]), "screen": json.loads(summary_path.read_text())})
    tax = load.tax_parcels(raw)
    homes = features.homes(load.parcels(raw), load.dwellings(raw), load.values_2025(raw), tax, load.centroids(raw / "gis"))
    sales, screen_summary = features.usable_sales(load.sales(raw), homes, load.transfers(raw))
    rates = verdict.tax_rates(tax, load.tax_detail(raw), homes)
    homes.to_parquet(paths["homes"])
    sales.to_parquet(paths["sales"])
    rates.to_parquet(paths["rates"])
    summary_path.write_text(json.dumps(screen_summary, indent=2))
    return homes, sales, {"rates": rates, "screen": screen_summary}


@dataclass
class Model:
    index: pd.Series
    hedonic: hedonic.Hedonic
    pool: pd.DataFrame          # comp sales joined to their homes, with restated log price
    months_old: np.ndarray


def fit(homes: pd.DataFrame, sales: pd.DataFrame) -> Model:
    """Everything here uses only validated 2023-2025 sales, which the county also had."""
    s = sales[sales["set"] == "comps"].copy()
    values = homes.set_index("pid")["value_2026"]
    index = timeindex.monthly_index(s, values)
    s["price_adj"] = timeindex.to_valuation_date(s, index)
    pool = s.merge(homes, on="pid", how="inner").reset_index(drop=True)
    model = hedonic.fit(pool, np.log(pool["price_adj"]))
    months = ((pd.Timestamp(VALUATION_DATE) - pool["date"]).dt.days / 30.44).clip(lower=0).to_numpy()
    return Model(index=index, hedonic=model, pool=pool, months_old=months)


def run_comps(subjects: pd.DataFrame, m: Model, exclude_self: bool) -> comps.CompResult:
    return comps.find(subjects.reset_index(drop=True), m.pool, np.log(m.pool["price_adj"].to_numpy()), m.months_old,
                      m.hedonic, exclude_self=exclude_self)


def bands(homes: pd.DataFrame, m: Model, blend: float, year: int = 2025) -> pd.DataFrame:
    """Likely range from validated sales in `year`, each estimated without its own sale. Too narrow for new sales
    (these are clean, and the model saw them), so it's kept only for comparison."""
    subj = m.pool[m.pool["date"].dt.year == year]
    r = run_comps(subj, m, exclude_self=True)
    est = comps.with_blend(r, blend)
    resid = np.log(subj["price_adj"].to_numpy()) - est
    return verdict.band_table(resid, r.spread)


def test_sales(homes: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    return sales[sales["set"] == "holdout"].merge(homes, on="pid").reset_index(drop=True)


def new_sale_errors(test: pd.DataFrame, m: Model, blend: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Estimates for 2026 sales (without their own sale), and log errors after removing the market's overall drift
    since January 1. Returns (est_log, spread, resid_log, drift)."""
    r = run_comps(test, m, exclude_self=True)
    est = comps.with_blend(r, blend)
    price = test["price"].to_numpy(float)
    drift = float(np.nanmedian(price / np.exp(est)))
    return est, r.spread, np.log(price / drift) - est, drift


def chance_model(homes: pd.DataFrame, sales: pd.DataFrame, m: Model, blend: float) -> np.ndarray:
    """Coefficients for the chance a home sells below its county value, fitted on every 2026 sale."""
    test = test_sales(homes, sales)
    est, spread, _, _ = new_sale_errors(test, m, blend)
    county = test["value_2026"].to_numpy(float)
    return verdict.fit_chance(np.log(county) - est, spread, est, test["price"].to_numpy(float) < county)


def production_bands(homes: pd.DataFrame, sales: pd.DataFrame, m: Model, blend: float, q=(0.10, 0.90)) -> pd.DataFrame:
    """The likely range shown on the site: calibrated on every 2026 sale. Conservative, because those sales
    aren't validated yet and include some that weren't at market."""
    est, spread, resid, _ = new_sale_errors(test_sales(homes, sales), m, blend)
    return verdict.band_table(resid, spread, q=q)
