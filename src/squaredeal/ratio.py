"""IAAO ratio-study statistics: how well assessed values line up with sale prices.

ratio = assessed value / sale price
- median ratio: the overall level (IAAO: 0.90-1.10)
- COD, coefficient of dispersion: average % distance from the median ratio (IAAO: 5-15 for older or mixed homes)
- PRD, price-related differential: mean ratio / value-weighted ratio (IAAO: 0.98-1.03; above means regressive)
- PRB, price-related bias: % change in ratio when value doubles (IAAO: -0.05 to +0.05; negative means regressive)
"""
from __future__ import annotations

import numpy as np

STANDARDS = {"median": (0.90, 1.10), "cod": (5.0, 15.0), "prd": (0.98, 1.03), "prb": (-0.05, 0.05)}


def trim(ratio: np.ndarray, k: float = 1.5) -> np.ndarray:
    """IAAO's interquartile-range outlier rule; returns a boolean mask of ratios kept."""
    q1, q3 = np.quantile(ratio, [0.25, 0.75])
    iqr = q3 - q1
    return (ratio >= q1 - k * iqr) & (ratio <= q3 + k * iqr)


def cod(ratio: np.ndarray) -> float:
    med = np.median(ratio)
    return float(100 * np.mean(np.abs(ratio - med)) / med)


def prd(value: np.ndarray, price: np.ndarray) -> float:
    r = value / price
    return float(np.mean(r) / (value.sum() / price.sum()))


def prb(value: np.ndarray, price: np.ndarray) -> float:
    """Regress % deviation from the median ratio on log2 of a value proxy (half price, half value / median ratio),
    which avoids the bias of sorting by either price or value alone."""
    r = value / price
    med = np.median(r)
    proxy = 0.5 * price + 0.5 * value / med
    x = np.log2(proxy)
    y = (r - med) / med
    x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum())


def study(value: np.ndarray, price: np.ndarray, boot: int = 1000, seed: int = 0, trimmed: bool = True) -> dict:
    """All four statistics with 95% bootstrap intervals (resampling sales)."""
    value, price = np.asarray(value, float), np.asarray(price, float)
    r = value / price
    keep = trim(r) if trimmed else np.ones(len(r), bool)
    value, price, r = value[keep], price[keep], r[keep]

    def stats(v, p):
        rr = v / p
        return np.array([np.median(rr), cod(rr), prd(v, p), prb(v, p)])

    point = stats(value, price)
    rng = np.random.default_rng(seed)
    draws = np.array([stats(value[i], price[i]) for i in (rng.integers(0, len(r), len(r)) for _ in range(boot))])
    lo, hi = np.percentile(draws, [2.5, 97.5], axis=0)
    out = {"n": int(len(r)), "trimmed": int((~keep).sum())}
    for j, name in enumerate(["median", "cod", "prd", "prb"]):
        a, b = STANDARDS[name]
        out[name] = {"value": round(float(point[j]), 4), "lo": round(float(lo[j]), 4), "hi": round(float(hi[j]), 4),
                     "meets_standard": bool(a <= point[j] <= b)}
    return out


def by_decile(value: np.ndarray, price: np.ndarray, sort_by: str = "proxy") -> list[dict]:
    """Median ratio in each tenth of homes. Sorting by price exaggerates regressivity, sorting by value hides it;
    the proxy (as in PRB) sits between the two."""
    value, price = np.asarray(value, float), np.asarray(price, float)
    r = value / price
    keep = trim(r)
    value, price, r = value[keep], price[keep], r[keep]
    key = {"price": price, "value": value, "proxy": 0.5 * price + 0.5 * value / np.median(r)}[sort_by]
    edges = np.quantile(key, np.linspace(0, 1, 11))
    bins = np.clip(np.searchsorted(edges, key, side="right") - 1, 0, 9)
    return [{"decile": d + 1, "n": int((bins == d).sum()), "median_price": float(np.median(price[bins == d])),
             "median_ratio": round(float(np.median(r[bins == d])), 4)} for d in range(10)]
