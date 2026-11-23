import type { Metadata } from "next";

import validation from "../../../public/data/validation.json";
import meta from "../../../public/data/meta.json";

export const metadata: Metadata = {
  title: "How the estimate works, and how it was tested",
  description: "Comparable sales, a hedonic model, and a test on 10,000 sales the estimate never saw.",
};

const pctf = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`;

export default function Page() {
  const v = validation;
  const t = v.by_verdict_check_half;
  const cal = v.chance_calibration_check_half.find((b) => b.from === 0.2) ?? v.chance_calibration_check_half[0];
  return (
    <article className="mx-auto max-w-3xl pt-10">
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">How the estimate works</h1>
      <p className="mt-3 text-lg text-copy">
        Square Deal estimates what each single-family home in Franklin County would have sold for on January 1, 2026, the date the
        county&apos;s 2026 values are set for, using only the county&apos;s own public data. Then it was tested on sales it had never
        seen.
      </p>

      <h2 className="mt-10 text-xl font-bold text-ink">The data</h2>
      <p className="mt-2 text-copy">
        The Franklin County Auditor publishes its appraisal records every month: each home&apos;s size, age, quality grade,
        condition, rooms, basement, lot, and value, and every recorded sale with the county&apos;s own judgment of whether it was a
        valid market sale. The estimate uses {v.comps_sales.toLocaleString()} single-family sales from 2023 to 2025 that the county
        marked valid. Condos, duplexes, and homes with more than one building are left out.
      </p>

      <h2 className="mt-8 text-xl font-bold text-ink">The estimate, in four steps</h2>
      <ol className="mt-2 list-decimal space-y-3 pl-5 text-copy">
        <li>
          <strong className="text-ink">Restate every sale to January 2026.</strong> A monthly price index tracks how the market moved:
          each month&apos;s median of sale price ÷ the home&apos;s 2026 value. Prices rose about 13% from early 2023 to the end of
          2025.
        </li>
        <li>
          <strong className="text-ink">Learn what each feature is worth.</strong> A regression of price on the home&apos;s features,
          within each of the county&apos;s {v.model.neighborhoods.toLocaleString()} appraisal neighborhoods, gives the adjustments: for
          example, a full grade of construction quality is worth about {pctf(Math.exp(v.model.coefficients.grade) - 1)}, and central air
          about {pctf(Math.exp(v.model.coefficients.central_air) - 1)}. Neighborhoods with few sales borrow from their ZIP code.
        </li>
        <li>
          <strong className="text-ink">Find the five most similar sales.</strong> Among the 40 nearest sales within two miles, the
          closest matches on distance, size, effective age, quality, neighborhood, and how recent the sale was. Each is adjusted for
          how it differs from your home.
        </li>
        <li>
          <strong className="text-ink">Blend.</strong> The estimate is {pctf(v.blend_on_comps)} the weighted average of the five adjusted
          sales and {pctf(1 - v.blend_on_comps)}{" "}the regression&apos;s own estimate. That mix had the lowest error on 2025 sales, each
          estimated without its own sale.
        </li>
      </ol>

      <h2 className="mt-10 text-xl font-bold text-ink">How it was tested</h2>
      <p className="mt-2 text-copy">
        The test set is {v.test_sales.toLocaleString()} single-family homes sold in 2026, after the valuation date. Nothing about those
        sales went into the estimate.
      </p>
      <p className="mt-2 text-copy">
        One catch: the county hasn&apos;t validated 2026 sales yet, and in 2025 only {pctf(v.screen.share_valid_2025_deed_screened)}{" "}of
        single-parcel deed sales turned out to be valid market sales. The rest (sales to or between companies, quick resales, sales
        never offered on the market) mostly sold below the county&apos;s value. So a second model learns the county&apos;s own
        validity calls from 2023&ndash;2025, using only facts known at the time of sale (never the price): whether the buyer or seller
        is a company, how recently the home last sold, the deed type, and the home. Trained on 2023&ndash;2024 and checked on 2025, it
        raises the share of valid sales from {pctf(v.screen.share_valid_2025_deed_screened)} to {pctf(v.screen.share_valid_2025_after_screen)}{" "}
        while keeping {pctf(v.screen.share_kept_2025)} of them. That leaves {v.screen.pending_2026_kept.toLocaleString()} of{" "}
        {v.screen.pending_2026_deed_screened.toLocaleString()} 2026 sales.
      </p>
      <div className="mt-4 overflow-x-auto rounded-lg border border-line bg-card">
        <table className="tabular w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr><th className="px-3 py-2 font-medium" /><th className="px-3 py-2 text-right font-medium">County&apos;s 2026 values</th><th className="px-3 py-2 text-right font-medium">Square Deal</th></tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <td className="px-3 py-2">Uniformity (COD, lower is better)</td>
              <td className="px-3 py-2 text-right">{v.accuracy.cod_county.toFixed(1)}</td>
              <td className="px-3 py-2 text-right font-semibold">{v.accuracy.cod_square_deal.toFixed(1)}</td>
            </tr>
            <tr>
              <td className="px-3 py-2">Typical miss vs. the sale price</td>
              <td className="px-3 py-2 text-right">{pctf(v.accuracy.median_abs_error_county, 1)}</td>
              <td className="px-3 py-2 text-right font-semibold">{pctf(v.accuracy.median_abs_error_square_deal, 1)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-copy">
        So the estimate is a little more accurate than the county&apos;s values, not dramatically. A home&apos;s value being above
        the estimate isn&apos;t enough on its own to say it&apos;s too high.
      </p>

      <h3 className="mt-6 text-lg font-semibold text-ink">How the verdict is decided</h3>
      <p className="mt-2 text-copy">
        The verdict answers one question: of homes like this one, how many sold for less than their county value? A logistic
        regression on the 2026 sales estimates that chance from three things: how far the county&apos;s value is above or below the
        estimate, how much the five comparable sales disagree, and the price level. A home is flagged <em>likely too high</em> when
        the county&apos;s value is above the estimate and most homes like it sold for less; <em>worth a closer look</em> at 3 in 10
        or more; and <em>looks low</em> when fewer than 1 in 10 did.
      </p>
      <p className="mt-2 text-copy">
        My first version flagged homes whose value was above the high end of a likely range. It over-flagged expensive homes,
        whose estimates are less certain than the comparable sales suggest, so I replaced it.
      </p>

      <h3 className="mt-6 text-lg font-semibold text-ink">Do the flags mean anything?</h3>
      <p className="mt-2 text-copy">
        Everything was fitted on a random half of the 2026 sales and checked on the other half. There, the predicted chances matched
        what happened (homes given about a {pctf(cal.predicted)} chance sold below their value {pctf(cal.observed)} of the time, for example), and the likely range held{" "}
        {pctf(v.likely_range.coverage_check_half)} of sale prices against an 80% target. By verdict:
      </p>
      <div className="mt-3 overflow-x-auto rounded-lg border border-line bg-card">
        <table className="tabular w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Verdict</th>
              <th className="px-3 py-2 text-right font-medium">Share of homes</th>
              <th className="px-3 py-2 text-right font-medium">Sold below county value</th>
              <th className="px-3 py-2 text-right font-medium">Sold 10%+ below</th>
            </tr>
          </thead>
          <tbody>
            {([["likely_high", "Likely too high"], ["closer_look", "Worth a closer look"], ["in_line", "In line"], ["low", "Looks low"]] as const).map(([k, label]) => (
              <tr key={k} className="border-b border-line last:border-0">
                <td className="px-3 py-2">{label} <span className="text-muted">({t[k].n.toLocaleString()} sales)</span></td>
                <td className="px-3 py-2 text-right">{pctf(t[k].share_of_sales, 1)}</td>
                <td className="px-3 py-2 text-right">{pctf(t[k].sold_below_county_value ?? 0)} <span className="text-muted">[{pctf(t[k].sold_below_ci?.[0] ?? 0)}–{pctf(t[k].sold_below_ci?.[1] ?? 0)}]</span></td>
                <td className="px-3 py-2 text-right">{pctf(t[k].sold_10pct_below ?? 0)}</td>
              </tr>
            ))}
            <tr><td className="px-3 py-2 text-muted">All homes</td><td /><td className="px-3 py-2 text-right text-muted">{pctf(v.base_rate_check_half.sold_below_county_value)}</td><td className="px-3 py-2 text-right text-muted">{pctf(v.base_rate_check_half.sold_10pct_below)}</td></tr>
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-copy">
        Homes flagged &quot;likely too high&quot; sold below their county value more than twice as often as homes overall. The group
        is small, so its interval is wide. Across the county, {meta.verdicts.likely_high.toLocaleString()} homes get that flag and{" "}
        {meta.verdicts.closer_look.toLocaleString()}{" "}get &quot;worth a closer look.&quot;
      </p>

      <h2 className="mt-10 text-xl font-bold text-ink">Limits</h2>
      <ul className="mt-2 list-disc space-y-2 pl-5 text-copy">
        <li>It only knows what the county&apos;s records say. A finished basement, new kitchen, or failing roof the county doesn&apos;t know about isn&apos;t in it.</li>
        <li>The range on each home is wide on purpose. It&apos;s calibrated on 2026 sales that include some that weren&apos;t at full market value.</li>
        <li>It&apos;s not an appraisal, and the Board of Revision weighs evidence its own way.</li>
        <li>Single-family homes only. Updated monthly from the county&apos;s files; values become final in December.</li>
      </ul>
      <p className="mt-8 text-copy">
        The code, the decision behind the project, and every number on this page are on{" "}
        <a href="https://github.com/ajthakkar/square-deal" className="text-accent underline underline-offset-4">GitHub</a>.
      </p>
    </article>
  );
}
