"""A hedonic price model: log price = neighborhood effect + home features.

Two uses: the size of each comp adjustment (e.g., what 100 more square feet are worth), and a model estimate
for every home. Neighborhood effects use the county's appraisal neighborhoods, shrunk toward the ZIP code's
effect when a neighborhood has few sales.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

STYLES = {"05": "ranch", "10": "cape_cod", "03": "multi_level", "02": "bi_level", "07": "old_style"}
FEATURES = ["log_sqft", "eff_age", "eff_age_sq", "grade", "condition", "baths", "beds", "basement", "fin_basement",
            "log_acres", "two_story", "central_air", *STYLES.values()]
SHRINK = 10  # a neighborhood with 10 sales gets half its own effect, half its ZIP's


def design(h: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=h.index)
    X["log_sqft"] = np.log(h["sqft"])
    X["eff_age"] = h["eff_age"] / 10
    X["eff_age_sq"] = (h["eff_age"] / 10) ** 2
    X["grade"] = h["grade"]
    X["condition"] = h["condition"]
    X["baths"] = h["baths"].clip(0, 6)
    X["beds"] = h["beds"].fillna(3).clip(0, 7)
    X["basement"] = h["basement"]
    X["fin_basement"] = (h["fin_basement"] / 100).clip(0, 30)
    X["log_acres"] = np.log(h["acres"].clip(0.02, 50))
    X["two_story"] = (h["stories"].fillna(1) >= 2).astype(float)
    X["central_air"] = h["central_air"]
    for code, name in STYLES.items():
        X[name] = (h["style"] == code).astype(float)
    return X[FEATURES].astype(float)


@dataclass
class Hedonic:
    beta: pd.Series
    nbhd: pd.Series
    zip: pd.Series
    overall: float
    resid_sd: float
    n: int
    counts: pd.Series = field(default_factory=pd.Series)

    def effect(self, nbhd: pd.Series, zip_: pd.Series) -> np.ndarray:
        e = nbhd.map(self.nbhd)
        e = e.fillna(zip_.map(self.zip)).fillna(self.overall)
        return e.to_numpy(float)

    def predict_log(self, homes: pd.DataFrame) -> np.ndarray:
        return design(homes).to_numpy() @ self.beta.to_numpy() + self.effect(homes["nbhd"], homes["zip"])


def _within(y: np.ndarray, X: np.ndarray, groups: np.ndarray) -> np.ndarray:
    codes, inv = np.unique(groups, return_inverse=True)
    counts = np.bincount(inv)
    ym = np.bincount(inv, y) / counts
    Xm = np.vstack([np.bincount(inv, X[:, j]) / counts for j in range(X.shape[1])]).T
    yd, Xd = y - ym[inv], X - Xm[inv]
    beta, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
    return beta


def fit(homes: pd.DataFrame, log_price: pd.Series) -> Hedonic:
    """`homes` rows aligned with `log_price` (one row per sale). One refit after dropping gross outliers."""
    X = design(homes).to_numpy()
    y = log_price.to_numpy(float)
    g = homes["nbhd"].to_numpy()
    keep = np.ones(len(y), bool)
    for _ in range(2):
        beta = _within(y[keep], X[keep], g[keep])
        r = y - X @ beta
        # neighborhood-demeaned residuals for outlier screening
        dm = pd.Series(r).groupby(g).transform("median").to_numpy()
        dev = r - dm
        mad = np.median(np.abs(dev[keep])) * 1.4826
        keep = np.abs(dev) < 4 * mad
    base = pd.Series(y - X @ beta)[keep]
    nb = base.groupby(g[keep]).agg(["mean", "size"])
    zp = base.groupby(homes["zip"].to_numpy()[keep]).agg(["mean", "size"])
    overall = float(base.mean())
    zip_eff = (zp["mean"] * zp["size"] + overall * SHRINK) / (zp["size"] + SHRINK)
    zip_of_nbhd = pd.Series(homes["zip"].to_numpy()[keep]).groupby(g[keep]).agg(lambda s: s.mode().iat[0])
    prior = zip_of_nbhd.map(zip_eff).fillna(overall)
    nb_eff = (nb["mean"] * nb["size"] + prior * SHRINK) / (nb["size"] + SHRINK)
    resid = base - pd.Series(g[keep]).map(nb_eff).to_numpy()
    return Hedonic(beta=pd.Series(beta, index=FEATURES), nbhd=nb_eff, zip=zip_eff, overall=overall,
                   resid_sd=float(resid.std()), n=int(keep.sum()), counts=nb["size"])
