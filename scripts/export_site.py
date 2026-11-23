"""Write the website's data: a result for every single-family home, the comparable sales, and the reports.

Output (site/public/data):
  meta.json         data date, counts, verdict totals
  streets.json      every street name -> shard number, with ZIP codes
  homes/<n>.json    one file per shard: street -> homes on it
  sales.json        the comparable sales the results point to
  report.json, validation.json

Run: python scripts/export_site.py   (after validate.py and report.py)
"""
from __future__ import annotations

import json
import shutil
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from squaredeal import comps, pipeline, verdict

SITE = pipeline.ROOT / "site" / "public" / "data"
RESULTS = pipeline.ROOT / "results"
SHARDS = 512
CODES = {verdict.NO_ESTIMATE: 0, verdict.IN_LINE: 1, verdict.CLOSER_LOOK: 2, verdict.LIKELY_HIGH: 3, verdict.LOW: 4}


def shard_of(street: str) -> int:
    return zlib.crc32(street.encode()) % SHARDS


def city_of(address: str) -> str:
    parts = [p.strip() for p in address.split(",")]
    return parts[1].title() if len(parts) >= 3 else ""


def num(x, digits=0):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return int(round(x)) if digits == 0 else round(float(x), digits)


def main():
    homes, sales, extra = pipeline.prepare()
    m = pipeline.fit(homes, sales)
    val = json.loads((RESULTS / "validation.json").read_text())
    blend = val["blend_on_comps"]
    comps.BLEND = blend
    table = pipeline.production_bands(homes, sales, m, blend)                    # 80%: used for the verdict
    middle = pipeline.production_bands(homes, sales, m, blend, q=(0.25, 0.75))  # middle half: shown as the range

    subj = homes[homes["modelable"]].reset_index(drop=True)
    r = pipeline.run_comps(subj, m, exclude_self=False)  # a home's own recent sale is the best evidence it has
    est = comps.with_blend(r, blend)
    lo, hi = verdict.apply_band(est, r.spread, table)
    mlo, mhi = verdict.apply_band(est, r.spread, middle)
    e, l, h = np.exp(est), np.exp(lo), np.exp(hi)
    coef = pipeline.chance_model(homes, sales, m, blend)
    gap = np.log(subj["value_2026"].to_numpy(float)) - est
    p = verdict.chance(coef, gap, r.spread, est)
    v = verdict.classify_chance(p, gap)
    excess = np.clip(subj["value_2026"].to_numpy(float) - e, 0, None)
    tax = verdict.yearly_tax_difference(excess, subj["tax_district"], extra["rates"])

    # Comparable sales referenced by any result, renumbered compactly
    used = np.unique(r.idx[r.idx >= 0])
    remap = np.full(len(m.pool), -1)
    remap[used] = np.arange(len(used))
    pool = m.pool.iloc[used]
    sales_rows = [[a, d.strftime("%Y-%m"), num(p), num(pa), num(sq), num(yb), num(bd), num(ba, 1), g or "", c or "",
                   num(la, 5), num(lo_, 5)]
                  for a, d, p, pa, sq, yb, bd, ba, g, c, la, lo_ in zip(
                      pool["address"], pool["date"], pool["price"], pool["price_adj"], pool["sqft"], pool["year_built"],
                      pool["beds"], pool["baths"], pool["grade_code"], pool["condition_word"], pool["lat"], pool["lon"])]

    res = pd.DataFrame({"pid": subj["pid"], "est": e, "lo50": np.exp(mlo), "hi50": np.exp(mhi), "lo": l, "hi": h,
                        "verdict": v, "tax": tax, "chance": p})
    res["comps"] = [[int(remap[i]) for i in row if i >= 0] for row in r.idx]
    res["adj"] = [[num(np.exp(a)) for a, i in zip(arow, irow) if i >= 0] for arow, irow in zip(r.adj_log, r.idx)]
    allh = homes.merge(res, on="pid", how="left")
    allh["verdict"] = allh["verdict"].fillna(verdict.NO_ESTIMATE)
    allh = allh[allh["street"].str.len() > 0]

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "homes").mkdir(parents=True)
    shards: dict[int, dict[str, list]] = {}
    streets: dict[str, set] = {}
    for row in allh.itertuples(index=False):
        rec = [num(row.number), row.address, row.pid, num(row.value_2025), num(row.value_2026),
               num(row.est), num(row.lo50), num(row.hi50), num(row.lo), num(row.hi), CODES[row.verdict], num(row.tax),
               num(row.sqft), num(row.year_built), num(row.beds), num(row.baths, 1), row.grade_code or "",
               row.condition_word or "", num(row.acres, 3), num(row.lat, 5), num(row.lon, 5),
               row.comps if isinstance(row.comps, list) else [], row.adj if isinstance(row.adj, list) else [],
               num(row.chance, 2)]
        shards.setdefault(shard_of(row.street), {}).setdefault(row.street, []).append(rec)
        streets.setdefault(row.street, set()).add((row.zip, city_of(row.address)))
    for n, content in shards.items():
        for k in content:
            content[k].sort(key=lambda rec: (rec[0] or 0, rec[1]))
        (SITE / "homes" / f"{n}.json").write_text(json.dumps(content, separators=(",", ":")))
    (SITE / "streets.json").write_text(json.dumps(
        [[s, shard_of(s), sorted({z for z, _ in zc if z}), sorted({c for _, c in zc if c})] for s, zc in sorted(streets.items())],
        separators=(",", ":")))
    (SITE / "sales.json").write_text(json.dumps(
        {"cols": ["address", "month", "price", "price_jan2026", "sqft", "year_built", "beds", "baths", "grade", "condition",
                  "lat", "lon"], "rows": sales_rows}, separators=(",", ":")))

    source = json.loads((pipeline.RAW / "source.json").read_text()) if (pipeline.RAW / "source.json").exists() else {}
    counts = allh["verdict"].value_counts().to_dict()
    meta = {
        "data_date": source.get("appraisal_date"), "homes": int(len(allh)), "estimated": int(np.isfinite(e).sum()),
        "verdicts": {k: int(counts.get(k, 0)) for k in CODES}, "comp_sales": int(len(used)),
        "verdict_codes": {str(v_): k for k, v_ in CODES.items()},
        "home_fields": ["number", "address", "pid", "value_2025", "value_2026", "estimate", "middle_low", "middle_high",
                        "low_80", "high_80", "verdict",
                        "yearly_tax_difference", "sqft", "year_built", "beds", "baths", "grade", "condition", "acres",
                        "lat", "lon", "comps", "adjusted_prices", "chance_sold_below_county_value"],
        "chance_coefficients": [round(float(c), 5) for c in coef],
        "range_80_table": table.round(4).replace([np.inf], None).to_dict(orient="records"),
        "range_middle_table": middle.round(4).replace([np.inf], None).to_dict(orient="records"),
        "tax_rate_note": "Yearly tax difference uses 2025 effective rates per tax district, scaled for the 2026 update, "
                         "for an owner-occupant with both homeowner credits.",
    }
    (SITE / "meta.json").write_text(json.dumps(meta, indent=1))
    for f in ["report.json", "validation.json"]:
        shutil.copy(RESULTS / f, SITE / f)
    size = sum(p.stat().st_size for p in SITE.rglob("*.json"))
    print(json.dumps(meta["verdicts"]), f"{len(shards)} shards, {len(streets)} streets, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
