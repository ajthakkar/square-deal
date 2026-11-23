import Link from "next/link";

import { HomeSearch } from "@/components/HomeSearch";
import meta from "../../public/data/meta.json";
import report from "../../public/data/report.json";
import validation from "../../public/data/validation.json";

const n = (x: number) => x.toLocaleString("en-US");

export default function Page() {
  const change = report.value_change_2025_to_2026.median;
  const flagged = meta.verdicts.likely_high + meta.verdicts.closer_look;
  return (
    <>
      <section className="pt-10 sm:pt-14">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Franklin County, Ohio · 2026 values</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-bold leading-tight text-ink sm:text-5xl">
          Is your new home value a square deal?
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-copy">
          Franklin County just updated every home&apos;s value for 2026, up about {Math.round(change * 100)}% for a typical
          single-family home. Enter your address to compare yours with what similar homes nearby actually sold for. It&apos;s free,
          and it takes a few seconds.
        </p>
        <div className="mt-8 rounded-xl border border-line bg-card p-5 shadow-sm sm:p-7">
          <HomeSearch />
        </div>
      </section>

      <section className="mt-14 grid gap-6 sm:grid-cols-3">
        <div>
          <h2 className="font-semibold text-ink">1. Find similar sales</h2>
          <p className="mt-1 text-copy">
            The five most similar nearby homes that sold from 2023 to 2025, using only sales the county itself marked as valid.
          </p>
        </div>
        <div>
          <h2 className="font-semibold text-ink">2. Adjust them to your home</h2>
          <p className="mt-1 text-copy">
            Each price is restated to January 2026 and adjusted for size, age, quality, condition, rooms, basement, and lot, the way
            an appraiser would.
          </p>
        </div>
        <div>
          <h2 className="font-semibold text-ink">3. Compare with the county</h2>
          <p className="mt-1 text-copy">
            If the county&apos;s value is above what those sales support, you&apos;ll see the evidence and how to file a free
            complaint by March 31, 2027.
          </p>
        </div>
      </section>

      <section className="mt-14 rounded-xl border border-line bg-card p-6 sm:p-8">
        <h2 className="text-xl font-bold text-ink">What it found across the county</h2>
        <dl className="mt-5 grid gap-6 sm:grid-cols-3">
          <div>
            <dt className="text-sm text-muted">Single-family homes checked</dt>
            <dd className="tabular text-3xl font-bold text-ink">{n(meta.estimated)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Values that look too high or worth a closer look</dt>
            <dd className="tabular text-3xl font-bold text-ink">{n(flagged)}</dd>
            <dd className="text-sm text-copy">{n(meta.verdicts.likely_high)} likely too high</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Accuracy on 2026 sales it never saw</dt>
            <dd className="tabular text-3xl font-bold text-ink">
              {(validation.accuracy.median_abs_error_square_deal * 100).toFixed(1)}%
            </dd>
            <dd className="text-sm text-copy">
              typical miss, vs. {(validation.accuracy.median_abs_error_county * 100).toFixed(1)}% for the county&apos;s values
            </dd>
          </div>
        </dl>
        <p className="mt-6 text-copy">
          Most homes are fine: the county&apos;s values are, on the whole, a little below what homes sell for, and they meet the
          professional standards for fairness. But values are set by formula for hundreds of thousands of homes at once, and some
          miss. <Link href="/fairness/" className="text-accent underline underline-offset-4">See the countywide numbers</Link>, or{" "}
          <Link href="/method/" className="text-accent underline underline-offset-4">how the estimate was tested</Link>.
        </p>
      </section>
    </>
  );
}
