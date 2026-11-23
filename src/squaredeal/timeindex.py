"""A monthly price index, so a 2023 sale can be compared with a value set as of January 1, 2026.

Method (sales ratio trend): every home has one fixed 2026 value, so the median of sale price / 2026 value
in each month tracks how the market moved. Smoothed with a centered 3-month rolling median.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import VALUATION_DATE


def monthly_index(sales: pd.DataFrame, values: pd.Series) -> pd.Series:
    """Index by month (Period), scaled so the valuation month is 1.0. `values` maps pid -> 2026 value."""
    v = sales["pid"].map(values)
    rel = np.log(sales["price"] / v)
    month = sales["date"].dt.to_period("M")
    raw = rel.groupby(month).median().sort_index()
    full = raw.reindex(pd.period_range(raw.index.min(), raw.index.max(), freq="M")).interpolate()
    smooth = full.rolling(3, center=True, min_periods=1).median()
    target = pd.Period(VALUATION_DATE, "M")
    # The valuation month may be after the last sale month in the data: hold the last level.
    level = smooth.iloc[-1] if target > smooth.index.max() else smooth.loc[target]
    return np.exp(smooth - level)


def to_valuation_date(sales: pd.DataFrame, index: pd.Series) -> pd.Series:
    """Sale price restated to the valuation date's market level."""
    month = sales["date"].dt.to_period("M")
    factor = month.map(index).astype(float)
    factor = factor.fillna(index.iloc[-1] if len(index) else 1.0)
    return sales["price"] / factor
