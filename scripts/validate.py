"""Test the estimate on 2026 sales it never saw, and compare with the county's own values.

Everything the estimate uses (comps, price index, model) comes from validated 2023-2025 sales, which the county
also had. The test sales happened after the January 1, 2026 valuation date, aren't validated by the county yet,
and are screened to single-parcel sales by warranty or survivorship deed.

The likely range is calibrated on a random half of the test sales and checked on the other half.

Run: python scripts/validate.py   ->  results/validation.json
"""
from __future__ import annotations

import json

import numpy as np

from squaredeal import comps, pipeline, ratio, verdict

OUT = pipeline.ROOT / "results"
BLENDS = [0.0, 0.25, 0.5, 0.75, 1.0]
SEED = 1


def cod_of(est, price):
    r = est / price
    return ratio.cod(r[ratio.trim(r)])


def choose_blend(m) -> tuple[float, dict]:
    """Pick the comps/model blend on 2025 sales (each estimated without its own sale), never on the test set."""
    subj = m.pool[m.pool["date"].dt.year == 2025]
    r = pipeline.run_comps(subj, m, exclude_self=True)
    price = subj["price_adj"].to_numpy()
    scores = {}
    for b in BLENDS:
        est = np.exp(comps.with_blend(r, b))
        ok = np.isfinite(est)
        scores[b] = round(cod_of(est[ok], price[ok]), 2)
    return min(scores, key=scores.get), scores


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """95% interval for a proportion; better than +/- 2 SE when n is small."""
    if n == 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(c - h), 4), round(float(c + h), 4)]


def verdict_table(v, price, county):
    below, below10 = price < county, price < 0.9 * county
    out = {}
    for name in [verdict.LIKELY_HIGH, verdict.CLOSER_LOOK, verdict.IN_LINE, verdict.LOW]:
        sel = v == name
        n = int(sel.sum())
        out[name] = {"n": n, "share_of_sales": round(float(sel.mean()), 4),
                     "sold_below_county_value": round(float(below[sel].mean()), 4) if n else None,
                     "sold_below_ci": wilson(int(below[sel].sum()), n),
                     "sold_10pct_below": round(float(below10[sel].mean()), 4) if n else None,
                     "sold_10pct_below_ci": wilson(int(below10[sel].sum()), n)}
    return out


def main():
    homes, sales, extra = pipeline.prepare()
    m = pipeline.fit(homes, sales)
    blend, blend_scores = choose_blend(m)
    test = pipeline.test_sales(homes, sales)
    est, spread, resid, drift = pipeline.new_sale_errors(test, m, blend)
    ok = np.isfinite(est)
    price, county = test["price"].to_numpy(float), test["value_2026"].to_numpy(float)
    e = np.exp(est)

    calib = np.random.default_rng(SEED).random(len(test)) < 0.5
    check = ~calib & ok
    gap = np.log(county) - est
    below = price < county

    # The likely range shown on the site
    table = verdict.band_table(resid[calib & ok], spread[calib & ok])
    lo, hi = verdict.apply_band(est, spread, table)
    covered = (price[check] / drift >= np.exp(lo[check])) & (price[check] / drift <= np.exp(hi[check]))
    narrow = pipeline.bands(homes, m, blend)
    nlo, nhi = verdict.apply_band(est, spread, narrow)
    narrow_cov = np.mean((price[ok] / drift >= np.exp(nlo[ok])) & (price[ok] / drift <= np.exp(nhi[ok])))

    # The verdict: fitted on one half, checked on the other
    coef = verdict.fit_chance(gap[calib & ok], spread[calib & ok], est[calib & ok], below[calib & ok])
    p = verdict.chance(coef, gap, spread, est)
    v = verdict.classify_chance(p[check], gap[check])
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 1.0]
    calibration = []
    for a, b in zip(bins[:-1], bins[1:]):
        sel = check & (p >= a) & (p < b)
        if sel.sum():
            calibration.append({"from": a, "to": b, "n": int(sel.sum()), "predicted": round(float(p[sel].mean()), 4),
                                "observed": round(float(below[sel].mean()), 4)})
    tiers = [0, 150e3, 250e3, 400e3, 600e3, 1e6, np.inf]
    by_tier = []
    for a, b in zip(tiers[:-1], tiers[1:]):
        sel = (county[check] >= a) & (county[check] < b)
        row = {"county_value_from": a, "county_value_to": None if b == np.inf else b, "n": int(sel.sum()),
               "base_sold_below": round(float(below[check][sel].mean()), 4)}
        for name in [verdict.LIKELY_HIGH, verdict.CLOSER_LOOK, verdict.IN_LINE, verdict.LOW]:
            row[name] = round(float((v[sel] == name).mean()), 4)
        by_tier.append(row)
    # The first version, for comparison: verdict from the likely range alone
    v_range = verdict.classify(county[check], e[check], np.exp(lo[check]), np.exp(hi[check]))

    result = {
        "test_sales": int(len(test)), "estimated": int(ok.sum()), "check_half": int(check.sum()),
        "comps_sales": int((sales["set"] == "comps").sum()),
        "screen": extra["screen"],
        "blend_on_comps": blend, "blend_cod_2025": blend_scores,
        "model": {"sales": m.hedonic.n, "neighborhoods": int(len(m.hedonic.nbhd)), "resid_sd": round(m.hedonic.resid_sd, 4),
                  "coefficients": m.hedonic.beta.round(4).to_dict()},
        "accuracy": {
            "cod_county": round(cod_of(county[ok], price[ok]), 2),
            "cod_square_deal": round(cod_of(e[ok], price[ok]), 2),
            "median_abs_error_county": round(float(np.median(np.abs(county[ok] / np.median(county[ok] / price[ok]) - price[ok]) / price[ok])), 4),
            "median_abs_error_square_deal": round(float(np.median(np.abs(e[ok] * drift - price[ok]) / price[ok])), 4),
            "price_drift_since_valuation_date": round(drift, 4),
        },
        "likely_range": {"target": 0.80, "coverage_check_half": round(float(covered.mean()), 4),
                         "coverage_if_calibrated_on_2025_sales": round(float(narrow_cov), 4),
                         "table": table.round(4).replace([np.inf], None).to_dict(orient="records")},
        "base_rate_check_half": {"sold_below_county_value": round(float((price[check] < county[check]).mean()), 4),
                                 "sold_10pct_below": round(float((price[check] < 0.9 * county[check]).mean()), 4)},
        "by_verdict_check_half": verdict_table(v, price[check], county[check]),
        "chance_calibration_check_half": calibration,
        "verdicts_by_price_tier_check_half": by_tier,
        "chance_coefficients_calibration_half": [round(float(c), 4) for c in coef],
        "first_version_range_verdicts_check_half": verdict_table(v_range, price[check], county[check]),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in result if k not in ("model",)}, indent=2))


if __name__ == "__main__":
    main()
