"""Which 2026 sales would the county likely accept as market sales?

The county validates sales months after they happen; most 2026 sales are still pending. In 2025, only about 70% of
single-parcel deed sales were later judged valid, and as few as 35% for homes under $150,000. The rest (sales between
relatives or companies, flips, sales never offered on the market) mostly sold below the county's value, so leaving them
in would make the county look worse than it is and send the wrong homes to the Board of Revision.

This learns the county's own validity calls from 2023-2025 using facts known at the time of sale, never the price:
whether the buyer or seller is a company, how recently the home last sold, the deed type, and the home itself.
Owner names are used only to compute the company flags and are dropped immediately.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

COMPANY = re.compile(
    r"\b(?:LLC|L L C|INC|CORP|CORPORATION|COMPANY|CO|LTD|LP|LLP|BANK|PROPERTIES|PROPERTY|HOLDINGS|INVESTMENTS?|HOMES|REALTY|"
    r"CAPITAL|GROUP|PARTNERS|FUND|ASSOCIATION|ASSN|SECRETARY|FEDERAL|MORTGAGE|TRUSTEE|ENTERPRISES|VENTURES|REO|SERIES)\b")
KEEP_AT = 0.6  # keep a pending sale when the county would likely call it valid


def transfer_flags(transfers: pd.DataFrame) -> pd.DataFrame:
    """Per transfer: is the new owner a company, was the previous owner one, and days since the previous transfer."""
    t = transfers.sort_values(["PARCEL ID", "date"]).copy()
    t["buyer_company"] = t["owner"].fillna("").str.upper().str.contains(COMPANY)
    t["seller_company"] = t.groupby("PARCEL ID")["buyer_company"].shift(1).fillna(False).astype(bool)
    t["days_since_previous"] = (t["date"] - t.groupby("PARCEL ID")["date"].shift(1)).dt.days
    return t.drop(columns=["owner"]).drop_duplicates(["PARCEL ID", "date"], keep="last")


def design(d: pd.DataFrame) -> np.ndarray:
    days = d["days_since_previous"].fillna(9000).clip(0, 9000)
    return np.c_[np.ones(len(d)), d["buyer_company"].astype(float), d["seller_company"].astype(float),
                 (days < 3 * 365).astype(float), np.log1p(days / 365), d["grade"].fillna(2), d["condition"].fillna(3),
                 d["eff_age"].fillna(40) / 10, np.log(d["value_2026"].clip(30000)),
                 d["INSTRUMENT"].str.startswith("SV").astype(float), d["INSTRUMENT"].str.startswith("LW").astype(float)]


def fit(d: pd.DataFrame, l2: float = 1e-2) -> np.ndarray:
    X, y = design(d), d["is_valid"].to_numpy(float)
    b = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ b))
        H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(b))
        step = np.linalg.solve(H, X.T @ (y - p) - l2 * b)
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return b


def predict(b: np.ndarray, d: pd.DataFrame) -> np.ndarray:
    return 1 / (1 + np.exp(-design(d) @ b))


def auc(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(score)
    rank = np.empty(len(score))
    rank[order] = np.arange(1, len(score) + 1)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((rank[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
