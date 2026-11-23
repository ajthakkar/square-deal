import type { Metadata } from "next";

import report from "../../../public/data/report.json";

export const metadata: Metadata = {
  title: "Are Franklin County's 2026 values fair?",
  description: "A ratio study of Franklin County's 2026 single-family home values against 2025 and 2026 sales, by the IAAO's standards.",
};

type Stat = { value: number; lo: number; hi: number; meets_standard: boolean | null };
type Study = { n: number; median: Stat; cod: Stat; prd: Stat; prb: Stat };

const ROWS: { key: keyof Omit<Study, "n">; label: string; standard: string; explain: string; fmt: (x: number) => string }[] = [
  { key: "median", label: "Median ratio", standard: "0.90 to 1.10", fmt: (x) => x.toFixed(3),
    explain: "County value ÷ sale price for the typical home. Below 1 means values run under sale prices." },
  { key: "cod", label: "Uniformity (COD)", standard: "5 to 15", fmt: (x) => x.toFixed(1),
    explain: "The average gap between a home's ratio and the typical ratio, in percent. Lower is more even." },
  { key: "prd", label: "Price-related differential (PRD)", standard: "0.98 to 1.03", fmt: (x) => x.toFixed(3),
    explain: "Above 1 means cheaper homes carry higher ratios than expensive ones." },
  { key: "prb", label: "Price-related bias (PRB)", standard: "−0.05 to +0.05", fmt: (x) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(3),
    explain: "How much the ratio changes when a home's value doubles. Negative means cheaper homes are valued closer to full price." },
];

export default function Page() {
  const a = report.in_sample_2025 as unknown as Study;
  const b = report.new_sales_2026 as unknown as Study;
  const chg = report.value_change_2025_to_2026;
  const nb = report.neighborhoods_2026;
  const decRaw = report.deciles_2026 as Record<string, { median_ratio: number }[]>;
  const dec = Object.fromEntries(Object.entries(decRaw).map(([k, v]) => [k, v.map((d) => d.median_ratio)])) as Record<"price" | "value" | "proxy", number[]>;
  return (
    <article className="pt-10">
      <h1 className="max-w-3xl text-3xl font-bold text-ink sm:text-4xl">Are the 2026 values fair across the county?</h1>
      <p className="mt-3 max-w-3xl text-lg text-copy">
        Mostly, yes. Judged against sales the county couldn&apos;t have used, Franklin County&apos;s 2026 values for single-family
        homes meet the professional standards for uniformity and for treating cheap and expensive homes alike. The misses are
        individual: about {Math.round(report.new_sales_share_below_value * 100)}% of homes sold in 2026 went for less than their county
        value, and {Math.round(report.new_sales_share_10pct_below * 100)}% for at least 10% less.
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-bold text-ink">The ratio study</h2>
        <p className="mt-2 max-w-3xl text-copy">
          Assessors check their work with a <em>ratio study</em>: divide each sold home&apos;s value by its sale price, then measure
          the level and spread of those ratios. The standards come from the International Association of Assessing Officers (IAAO).
        </p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-line bg-card">
          <table className="tabular w-full min-w-[680px] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">Measure</th>
                <th className="px-3 py-2 font-medium">IAAO standard</th>
                <th className="px-3 py-2 font-medium">2025 sales the county used ({a.n.toLocaleString()})</th>
                <th className="px-3 py-2 font-medium">2026 sales it didn&apos;t ({b.n.toLocaleString()})</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr key={r.key} className="border-b border-line align-top last:border-0">
                  <td className="px-3 py-3">
                    <span className="font-semibold text-ink">{r.label}</span>
                    <span className="mt-1 block text-muted">{r.explain}</span>
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">{r.standard}</td>
                  <Cell s={a[r.key]} fmt={r.fmt} />
                  <Cell s={b[r.key]} fmt={r.fmt} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-sm text-muted">
          Brackets are 95% bootstrap intervals. Outliers are trimmed by the IAAO&apos;s interquartile rule. 2026 sale prices are not
          restated to January 1; prices rose about 3% after it, which pulls that median ratio down.
        </p>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-bold text-ink">Do cheaper homes get higher values?</h2>
        <p className="mt-2 max-w-3xl text-copy">
          A common finding nationally, from University of Chicago research, is that cheaper homes are valued closer to their full
          price than expensive ones. Here, sorting the 2026 sales by price makes the cheapest tenth look valued at{" "}
          {dec.price[0].toFixed(2)} of its price against {dec.price[9].toFixed(2)}{" "}for the most expensive; sorting by the county&apos;s
          value flips it ({dec.value[0].toFixed(2)} against {dec.value[9].toFixed(2)}). Both are statistical artifacts of sorting on a
          noisy number. The IAAO&apos;s method, which sorts by a mix of the two, gives {dec.proxy[0].toFixed(2)} for the cheapest tenth
          and {dec.proxy[9].toFixed(2)} for the most expensive, and the price-related bias is {fmtPrb(b.prb.value)}, inside the standard.
        </p>
        <p className="mt-2 max-w-3xl text-copy">
          One caution: 2026 sales aren&apos;t validated by the county yet. Before screening out likely non-market sales (sales to or
          between companies, quick resales), the cheapest homes looked over-valued. Most of that came from those sales.
        </p>
        <DecileChart />
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-bold text-ink">By school district</h2>
        <p className="mt-2 max-w-3xl text-copy">
          2026 sales, districts with at least 100. A higher median ratio means the district&apos;s homes are valued closer to their
          sale prices than elsewhere, so their owners carry a slightly larger share. Value change is the median change from 2025 to
          2026 for every single-family home in the district.
        </p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-line bg-card">
          <table className="tabular w-full min-w-[560px] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">School district</th>
                <th className="px-3 py-2 text-right font-medium">Sales</th>
                <th className="px-3 py-2 text-right font-medium">Median ratio</th>
                <th className="px-3 py-2 text-right font-medium">COD</th>
                <th className="px-3 py-2 text-right font-medium">Value change</th>
              </tr>
            </thead>
            <tbody>
              {report.school_districts_2026.map((d) => {
                const c = (chg.by_school_district as Record<string, number>)[d.school_district];
                return (
                  <tr key={d.school_district} className="border-b border-line last:border-0">
                    <td className="px-3 py-2">{d.school_district.replace(/ Csd$/, " City").replace(/ Lsd$/, " Local").replace(/ Evsd$/, " Exempted Village")}</td>
                    <td className="px-3 py-2 text-right">{d.sales.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{d.median.value.toFixed(3)}</td>
                    <td className="px-3 py-2 text-right">{d.cod.value.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right">{c != null ? `${c >= 0 ? "+" : "−"}${Math.abs(c * 100).toFixed(1)}%` : "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-12 max-w-3xl">
        <h2 className="text-xl font-bold text-ink">Neighborhoods</h2>
        <p className="mt-2 text-copy">
          Of the {nb.neighborhoods} county appraisal neighborhoods with at least {nb.min_sales} sales in 2026, the middle 90% have a
          median ratio within {Math.round((1 - nb.relative_median_5_50_95[0]) * 100)}% below to{" "}
          {Math.round((nb.relative_median_5_50_95[2] - 1) * 100)}% above the county&apos;s. Only {nb.clearly_above_county_by_5pct} are
          clearly more than 5% above it, and {nb.clearly_below_county_by_5pct} clearly more than 5% below.
        </p>
      </section>

      <section className="mt-12 max-w-3xl">
        <h2 className="text-xl font-bold text-ink">One thing to watch for</h2>
        <p className="mt-2 text-copy">
          A ratio study on the same sales the county used to set its values flatters the county, because the values were fitted to
          them. That&apos;s why the first column looks nearly perfect (a COD of {a.cod.value.toFixed(1)}). The second column uses sales
          from after the valuation date, which is the honest test. I also checked that homes which sold weren&apos;t valued
          differently from similar homes that didn&apos;t (&quot;sales chasing&quot;): within the same neighborhood, the change in
          value differed by about 0.3 percentage points.
        </p>
      </section>
    </article>
  );
}

const fmtPrb = (x: number) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(3);

function Cell({ s, fmt }: { s: Stat; fmt: (x: number) => string }) {
  const badge = s.meets_standard == null ? null : s.meets_standard
    ? <span className="ml-2 rounded bg-ok-soft px-1.5 py-0.5 text-xs font-semibold text-ok">meets</span>
    : <span className="ml-2 rounded bg-bad-soft px-1.5 py-0.5 text-xs font-semibold text-bad">misses</span>;
  return (
    <td className="px-3 py-3 whitespace-nowrap">
      <span className="font-semibold text-ink">{fmt(s.value)}</span>{badge}
      <span className="block text-muted">[{fmt(s.lo)}, {fmt(s.hi)}]</span>
    </td>
  );
}

function DecileChart() {
  const series = [
    { key: "price", label: "Sorted by sale price", color: "var(--bad)" },
    { key: "proxy", label: "IAAO method", color: "var(--ink)" },
    { key: "value", label: "Sorted by county value", color: "var(--info)" },
  ] as const;
  const data = report.deciles_2026 as Record<string, { decile: number; median_ratio: number }[]>;
  const all = series.flatMap((s) => data[s.key].map((d) => d.median_ratio));
  const lo = Math.floor(Math.min(...all) * 50) / 50;
  const hi = Math.ceil(Math.max(...all) * 50) / 50;
  const W = 720, H = 300, L = 48, R = 160, T = 16, B = 40;
  const x = (d: number) => L + ((d - 1) / 9) * (W - L - R);
  const y = (r: number) => T + (1 - (r - lo) / (hi - lo)) * (H - T - B);
  const ticks = Array.from({ length: Math.round((hi - lo) / 0.025) + 1 }, (_, i) => lo + i * 0.025);
  return (
    <figure className="mt-5 overflow-x-auto rounded-lg border border-line bg-card p-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[560px]" role="img"
        aria-label={series.map((s) => `${s.label}: ${data[s.key][0].median_ratio.toFixed(2)} for the cheapest tenth, ${data[s.key][9].median_ratio.toFixed(2)} for the most expensive`).join(". ")}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={L - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{t.toFixed(3)}</text>
          </g>
        ))}
        {Array.from({ length: 10 }, (_, i) => (
          <text key={i} x={x(i + 1)} y={H - B + 18} textAnchor="middle" fontSize="11" fill="var(--muted)">{i + 1}</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" fontSize="12" fill="var(--muted)">Tenth of homes, cheapest (1) to most expensive (10)</text>
        {series.map((s) => {
          const pts = data[s.key];
          const last = pts[pts.length - 1];
          return (
            <g key={s.key}>
              <polyline fill="none" stroke={s.color} strokeWidth="2" points={pts.map((p) => `${x(p.decile)},${y(p.median_ratio)}`).join(" ")} />
              {pts.map((p) => <circle key={p.decile} cx={x(p.decile)} cy={y(p.median_ratio)} r="4" fill={s.color} stroke="var(--card)" strokeWidth="2" />)}
              <text x={x(10) + 10} y={y(last.median_ratio) + 4} fontSize="12" fill={s.color}>{s.label}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 text-sm text-muted">Median of county value ÷ sale price in each tenth of the 2026 sales.</figcaption>
    </figure>
  );
}
