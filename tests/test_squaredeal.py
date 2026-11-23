import numpy as np
import pandas as pd
import pytest

from squaredeal import comps, features, hedonic, ratio, timeindex, verdict


def test_grade_and_codes():
    assert features.grade_score("C - AVERAGE QUALITY") == 2.0
    assert features.grade_score("C+1 - AVERAGE +") == pytest.approx(2 + 1 / 3)
    assert features.grade_score("B-2 - GOOD - -") == pytest.approx(3 - 2 / 3)
    assert np.isnan(features.grade_score(None))
    assert features.lead_code("B - FULL BASEMENT") == "B"
    assert features.street_key("W", "PACEMONT", "RD", None) == "W PACEMONT RD"


def test_ratio_statistics_on_known_data():
    price = np.array([100.0, 200.0, 300.0, 400.0])
    value = price * np.array([0.9, 1.0, 1.1, 1.0])
    r = value / price
    assert ratio.cod(r) == pytest.approx(100 * np.mean(np.abs(r - 1.0)) / 1.0)
    assert ratio.prd(price.copy(), price.copy()) == pytest.approx(1.0)
    # uniform assessment: no price-related bias
    assert ratio.prb(price * 0.9, price) == pytest.approx(0.0, abs=1e-12)


def test_prb_detects_regressive_assessment():
    rng = np.random.default_rng(0)
    price = np.exp(rng.uniform(np.log(100_000), np.log(800_000), 4000))
    value = price * (1.2 - 0.1 * np.log2(price / 100_000))  # cheaper homes assessed at higher ratios
    assert ratio.prb(value, price) < -0.05
    assert ratio.prd(value, price) > 1.03


def test_trim_drops_extreme_ratios():
    r = np.r_[np.full(99, 1.0) + np.linspace(-0.05, 0.05, 99), 5.0]
    assert ratio.trim(r).sum() == 99


def test_time_index_recovers_market_growth():
    rng = np.random.default_rng(1)
    n = 6000
    dates = pd.to_datetime("2023-01-15") + pd.to_timedelta(rng.integers(0, 365 * 3, n), unit="D")
    months = (dates.year - 2023) * 12 + dates.month - 1
    value = rng.uniform(150_000, 600_000, n)
    level = 1.005 ** (months - 35)  # 0.5% a month, 1.0 in Dec 2025
    price = value * level * np.exp(rng.normal(0, 0.05, n))
    sales = pd.DataFrame({"pid": np.arange(n), "date": dates, "price": price})
    idx = timeindex.monthly_index(sales, pd.Series(value, index=np.arange(n)))
    assert idx.iloc[-1] == pytest.approx(1.0, abs=0.02)
    assert idx.iloc[0] == pytest.approx(1.005 ** -35, abs=0.03)
    restated = timeindex.to_valuation_date(sales, idx)
    assert np.median(np.log(restated / value)) == pytest.approx(0.0, abs=0.02)


def synthetic_homes(n, rng, nbhds=20):
    h = pd.DataFrame({
        "pid": [f"P{i}" for i in range(n)],
        "nbhd": rng.integers(0, nbhds, n).astype(str), "zip": "43201",
        "sqft": rng.uniform(900, 3500, n), "eff_age": rng.uniform(0, 80, n), "grade": rng.choice([1.67, 2.0, 2.33, 3.0], n),
        "condition": rng.choice([2, 3, 4], n).astype(float), "baths": rng.choice([1, 1.5, 2, 2.5, 3], n),
        "beds": rng.choice([2, 3, 4], n).astype(float), "basement": rng.choice([0, 0.5, 1.0], n),
        "fin_basement": rng.choice([0, 400], n).astype(float), "acres": rng.uniform(0.1, 0.5, n),
        "stories": rng.choice([1, 2], n).astype(float), "central_air": 1.0, "style": "01",
    })
    h["x"] = h["nbhd"].astype(int) * 3000 + rng.uniform(0, 1500, n)
    h["y"] = rng.uniform(0, 1500, n)
    return h


def test_hedonic_recovers_size_and_grade_effects():
    rng = np.random.default_rng(2)
    h = synthetic_homes(5000, rng)
    nb_effect = h["nbhd"].astype(int) * 0.03
    logp = 12 + 0.5 * np.log(h["sqft"] / 1500) + 0.15 * h["grade"] + nb_effect + rng.normal(0, 0.05, len(h))
    m = hedonic.fit(h, logp)
    assert m.beta["log_sqft"] == pytest.approx(0.5, abs=0.03)
    assert m.beta["grade"] == pytest.approx(0.15, abs=0.02)
    assert np.corrcoef(m.predict_log(h), logp)[0, 1] > 0.95


def test_comps_exclude_self_and_adjust_for_size():
    rng = np.random.default_rng(3)
    h = synthetic_homes(3000, rng, nbhds=5)
    logp = 12 + 0.5 * np.log(h["sqft"] / 1500) + rng.normal(0, 0.03, len(h))
    m = hedonic.fit(h, logp)
    months = np.zeros(len(h))
    r = comps.find(h.iloc[:200], h, logp.to_numpy(), months, m, exclude_self=True)
    chosen = r.idx[r.idx >= 0]
    assert not np.any(chosen.reshape(200, -1) == np.arange(200)[:, None])  # a home is never its own comp
    est = comps.with_blend(r, 1.0)
    err = est - logp.iloc[:200].to_numpy()
    assert np.median(np.abs(err)) < 0.05
    r_self = comps.find(h.iloc[:200], h, logp.to_numpy(), months, m, exclude_self=False)
    assert (r_self.idx[:, 0] == np.arange(200)).mean() > 0.9  # with its own sale allowed, it's the best match


def test_verdicts_and_bands():
    table = pd.DataFrame({"spread_lo": [0, 0.05], "spread_hi": [0.05, np.inf], "q_lo": [-0.1, -0.2], "q_hi": [0.1, 0.2]})
    est = np.log(np.array([100.0, 100.0, 100.0, 100.0, np.nan]))
    lo, hi = verdict.apply_band(est, np.array([0.01, 0.01, 0.01, 0.2, np.nan]), table)
    assert np.exp(hi[0]) == pytest.approx(100 * np.exp(0.1))
    assert np.exp(hi[3]) == pytest.approx(100 * np.exp(0.2))
    v = verdict.classify(np.array([120, 105, 95, 50, 100]), np.exp(est), np.exp(lo), np.exp(hi))
    assert list(v) == [verdict.LIKELY_HIGH, verdict.CLOSER_LOOK, verdict.IN_LINE, verdict.LOW, verdict.NO_ESTIMATE]
