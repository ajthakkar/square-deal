"""Countywide fairness report: how well the 2026 values line up with sale prices, by the IAAO's measures.

Two views:
- 2025 sales the county validated. The county used these to set the values, so they look better than reality.
- 2026 sales after the valuation date (screened, not yet validated). The honest test.

Run: python scripts/report.py   ->  results/report.json, results/*.png
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from squaredeal import pipeline, ratio, timeindex  # noqa: E402

OUT = pipeline.ROOT / "results"
INK, MUTED, GRID, BLUE, ORANGE = "#1f1f1f", "#6b6b6b", "#e6e6e6", "#2a6f97", "#c2571a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
                     "savefig.bbox": "tight"})


def nbhd_spread(df: pd.DataFrame, county_median: float, min_sales: int = 20, boot: int = 400) -> dict:
    rng = np.random.default_rng(0)
    rows = []
    for nb, g in df.groupby("nbhd"):
        if len(g) < min_sales:
            continue
        r = g["ratio"].to_numpy()
        draws = np.median(r[rng.integers(0, len(r), (boot, len(r)))], axis=1)
        lo, hi = np.percentile(draws, [2.5, 97.5])
        rows.append((nb, len(g), np.median(r), lo, hi))
    t = pd.DataFrame(rows, columns=["nbhd", "n", "median", "lo", "hi"])
    rel = t["median"] / county_median
    return {"neighborhoods": int(len(t)), "min_sales": min_sales,
            "relative_median_5_50_95": [round(float(q), 3) for q in rel.quantile([0.05, 0.5, 0.95])],
            "clearly_above_county_by_5pct": int((t["lo"] > 1.05 * county_median).sum()),
            "clearly_below_county_by_5pct": int((t["hi"] < 0.95 * county_median).sum())}


def main():
    homes, sales, _ = pipeline.prepare()
    m = pipeline.fit(homes, sales)
    s = sales.merge(homes[["pid", "value_2025", "value_2026", "school", "nbhd"]], on="pid")
    s["price_adj"] = s["price"]
    c = s["set"] == "comps"
    s.loc[c, "price_adj"] = timeindex.to_valuation_date(s[c], m.index)
    s["ratio"] = s["value_2026"] / s["price_adj"]

    in_sample = s[c & (s["date"].dt.year == 2025)]
    new = s[s["set"] == "holdout"].copy()
    keep = ratio.trim(new["ratio"].to_numpy())
    new_t = new[keep]
    county_median = float(np.median(new_t["ratio"]))

    schools = []
    for name, g in new.groupby("school"):
        if len(g) >= 100:
            st = ratio.study(g["value_2026"], g["price"], boot=400)
            schools.append({"school_district": name.title(), "sales": st["n"], "median": st["median"], "cod": st["cod"]})
    schools.sort(key=lambda d: -d["median"]["value"])

    change = homes["value_2026"] / homes["value_2025"]
    change = change[np.isfinite(change) & (homes["value_2025"] > 0)]
    by_school_change = (homes.assign(chg=homes["value_2026"] / homes["value_2025"]).query("value_2025 > 0")
                        .groupby("school")["chg"].median().sort_values(ascending=False))

    report = {
        "homes": int(len(homes)),
        "value_change_2025_to_2026": {"median": round(float(change.median() - 1), 4),
                                      "p10": round(float(change.quantile(0.1) - 1), 4), "p90": round(float(change.quantile(0.9) - 1), 4),
                                      "share_over_20pct": round(float((change > 1.2).mean()), 4),
                                      "by_school_district": {k.title(): round(float(v - 1), 4) for k, v in by_school_change.items() if k}},
        "in_sample_2025": ratio.study(in_sample["value_2026"], in_sample["price_adj"]),
        "new_sales_2026": ratio.study(new["value_2026"], new["price"]),
        "new_sales_share_below_value": round(float((new["price"] < new["value_2026"]).mean()), 4),
        "new_sales_share_10pct_below": round(float((new["price"] < 0.9 * new["value_2026"]).mean()), 4),
        "deciles_2026": {k: ratio.by_decile(new["value_2026"], new["price"], k) for k in ["price", "value", "proxy"]},
        "school_districts_2026": schools,
        "neighborhoods_2026": nbhd_spread(new_t, county_median),
        "standards": ratio.STANDARDS,
    }
    # 2026 prices aren't restated to January 1 (they rose about 3% after it), so the level check doesn't apply.
    report["new_sales_2026"]["median"]["meets_standard"] = None
    report["new_sales_2026"]["note"] = "Sale prices are not restated to the January 1, 2026 valuation date."
    OUT.mkdir(exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2))

    # Chart: the same 2026 sales split into tenths three ways
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for key, color, label in [("price", ORANGE, "sorted by sale price"), ("proxy", INK, "IAAO-style (price and value)"),
                              ("value", BLUE, "sorted by county value")]:
        d = report["deciles_2026"][key]
        y = [r["median_ratio"] for r in d]
        ax.plot(range(1, 11), y, marker="o", ms=4, lw=2, color=color)
        ax.annotate(label, (10.15, y[-1]), va="center", fontsize=9, color=color)
    ax.set_xticks(range(1, 11))
    ax.set_xlim(0.7, 13.6)
    ax.set_xlabel("Tenth of homes, cheapest (1) to most expensive (10)")
    ax.set_ylabel("Median county value / sale price")
    ax.grid(axis="y", color=GRID)
    ax.set_title("Do cheaper homes get higher values? Depends how you sort (2026 sales)", loc="left", fontsize=11, color=INK)
    fig.savefig(OUT / "deciles.png")
    plt.close(fig)

    v = json.loads((OUT / "validation.json").read_text())
    names = [("likely_high", "Likely too high"), ("closer_look", "Worth a closer look"), ("in_line", "In line"), ("low", "Looks low")]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    base = v["base_rate_check_half"]["sold_below_county_value"]
    for i, (k, label) in enumerate(names):
        d = v["by_verdict_check_half"][k]
        p, (lo, hi) = d["sold_below_county_value"], d["sold_below_ci"]
        ax.errorbar(100 * p, i, xerr=[[100 * (p - lo)], [100 * (hi - p)]], fmt="o", ms=7, color=BLUE, elinewidth=1.6)
        ax.annotate(f"{100 * p:.0f}%  ({d['n']:,} sales)", (100 * hi + 1.5, i), va="center", fontsize=9, color=MUTED)
    ax.axvline(100 * base, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.annotate(f"all sales: {100 * base:.0f}%", (100 * base + 1, -0.65), fontsize=9, color=MUTED)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([n for _, n in names])
    ax.set_ylim(len(names) - 0.5, -0.9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of 2026 sales that sold for less than the county's value (95% interval)")
    ax.grid(axis="x", color=GRID)
    ax.set_title("Homes the tool flags really did sell below their county value more often", loc="left", fontsize=11, color=INK)
    fig.savefig(OUT / "verdicts.png")
    plt.close(fig)
    print(json.dumps({k: report[k] for k in ["value_change_2025_to_2026", "in_sample_2025", "new_sales_2026",
                                              "new_sales_share_below_value", "neighborhoods_2026"]}, indent=1)[:3500])


if __name__ == "__main__":
    main()
