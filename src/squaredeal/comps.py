"""Comparable sales: for each home, the most similar nearby sales, adjusted the way an appraiser would.

Each comp's price is restated to January 1, 2026, then adjusted for differences in size, age, quality,
condition, rooms, basement, lot, style, and neighborhood, using the hedonic model's coefficients.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .hedonic import Hedonic, design

K = 5                 # comps shown and averaged
CANDIDATES = 40       # nearest sales considered
RADIUS_FT = 2 * 5280  # never look farther than two miles
MIN_COMPS = 3
BLEND = 0.5           # weight on the comps estimate vs. the model estimate (set from validation)


@dataclass
class CompResult:
    est_log: np.ndarray      # blended estimate, log dollars
    comps_log: np.ndarray    # comps-only estimate
    model_log: np.ndarray    # model-only estimate
    spread: np.ndarray       # weighted SD of the comps' adjusted log prices
    n_comps: np.ndarray
    idx: np.ndarray          # (n, K) row numbers into the comp table, -1 where missing
    adj_log: np.ndarray      # (n, K) adjusted log prices
    score: np.ndarray        # (n, K) dissimilarity, lower is closer


def similarity(dist_ft, d_log_sqft, d_age, d_grade, other_nbhd, months_old):
    """Dissimilarity score; each term is scaled so 1.0 is a meaningful difference."""
    return (dist_ft / 2640 + np.abs(d_log_sqft) / 0.15 + np.abs(d_age) / 15 + np.abs(d_grade) / 0.67
            + 1.0 * other_nbhd + months_old / 24)


def find(subjects: pd.DataFrame, comp_homes: pd.DataFrame, comp_log_price: np.ndarray, comp_months_old: np.ndarray,
         model: Hedonic, exclude_self: bool = True, chunk: int = 20000) -> CompResult:
    """`comp_homes` is one row per comp sale (home features at the time of the data), aligned with the arrays."""
    beta = model.beta.to_numpy()
    Xs, Xc = design(subjects).to_numpy(), design(comp_homes).to_numpy()
    Es = model.effect(subjects["nbhd"], subjects["zip"])
    Ec = model.effect(comp_homes["nbhd"], comp_homes["zip"])
    ls = Xs @ beta + Es                        # subject's model log value
    lc = comp_log_price - (Xc @ beta + Ec)     # comp's price with its own features removed
    tree = cKDTree(comp_homes[["x", "y"]].to_numpy())
    m = len(comp_homes)

    n = len(subjects)
    out_idx = np.full((n, K), -1)
    out_adj = np.full((n, K), np.nan)
    out_score = np.full((n, K), np.nan)
    s_xy = subjects[["x", "y"]].to_numpy()
    s_pid = subjects["pid"].to_numpy()
    c_pid = comp_homes["pid"].to_numpy()
    s_sqft, c_sqft = np.log(subjects["sqft"].to_numpy(float)), np.log(comp_homes["sqft"].to_numpy(float))
    s_age, c_age = subjects["eff_age"].to_numpy(float), comp_homes["eff_age"].to_numpy(float)
    s_grade, c_grade = subjects["grade"].to_numpy(float), comp_homes["grade"].to_numpy(float)
    s_nb, c_nb = subjects["nbhd"].to_numpy(), comp_homes["nbhd"].to_numpy()

    for a in range(0, n, chunk):
        b = min(a + chunk, n)
        dist, idx = tree.query(s_xy[a:b], k=CANDIDATES, distance_upper_bound=RADIUS_FT)
        valid = idx < m
        safe = np.where(valid, idx, 0)
        sc = similarity(dist, s_sqft[a:b, None] - c_sqft[safe], s_age[a:b, None] - c_age[safe],
                        s_grade[a:b, None] - c_grade[safe], s_nb[a:b, None] != c_nb[safe], comp_months_old[safe])
        sc = np.where(valid, sc, np.inf)
        if exclude_self:
            sc = np.where(c_pid[safe] == s_pid[a:b, None], np.inf, sc)
        top = np.argsort(sc, axis=1)[:, :K]
        rows = np.arange(b - a)[:, None]
        best_sc, best_idx = sc[rows, top], safe[rows, top]
        ok = np.isfinite(best_sc)
        out_idx[a:b] = np.where(ok, best_idx, -1)
        out_score[a:b] = np.where(ok, best_sc, np.nan)
        out_adj[a:b] = np.where(ok, lc[best_idx] + ls[a:b, None], np.nan)

    w = np.where(np.isfinite(out_score), 1 / (1 + out_score), 0.0)
    n_comps = (w > 0).sum(1)
    wsum = np.where(n_comps > 0, w.sum(1), 1)
    comps_log = np.nansum(w * np.nan_to_num(out_adj), 1) / wsum
    spread = np.sqrt(np.nansum(w * (np.nan_to_num(out_adj) - comps_log[:, None]) ** 2 * (w > 0), 1) / wsum)
    comps_log = np.where(n_comps >= MIN_COMPS, comps_log, np.nan)
    est = np.where(np.isfinite(comps_log), BLEND * comps_log + (1 - BLEND) * ls, np.nan)
    return CompResult(est_log=est, comps_log=comps_log, model_log=ls, spread=np.where(n_comps >= MIN_COMPS, spread, np.nan),
                      n_comps=n_comps, idx=out_idx, adj_log=out_adj, score=out_score)


def with_blend(r: CompResult, blend: float) -> np.ndarray:
    return np.where(np.isfinite(r.comps_log), blend * r.comps_log + (1 - blend) * r.model_log, np.nan)
