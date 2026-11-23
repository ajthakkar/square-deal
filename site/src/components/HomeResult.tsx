"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RangeBar } from "./RangeBar";
import { loadSales, miles, money, monthLabel, pct, roundMoney, type Home, type Sale } from "@/lib/homes";
import { TONE_CLASSES, VERDICT, chanceSentence } from "@/lib/verdicts";

const DEADLINE = "March 31, 2027";

export function HomeResult({ home }: { home: Home }) {
  const [sales, setSales] = useState<Sale[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const v = VERDICT[home.verdict];
  const hasEstimate = home.verdict !== "no_estimate" && home.estimate != null;

  useEffect(() => {
    if (!hasEstimate) return;
    loadSales().then(setSales).catch((e) => setError(String(e)));
  }, [hasEstimate]);

  const change = home.value2025 && home.value2026 ? home.value2026 / home.value2025 - 1 : null;
  const gap = hasEstimate && home.value2026 ? home.value2026 / home.estimate! - 1 : null;
  const showTax = (home.verdict === "likely_high" || home.verdict === "closer_look") && (home.yearlyTax ?? 0) >= 20;

  return (
    <article className="rise mt-8 space-y-8" aria-live="polite">
      <div>
        <p className="text-sm uppercase tracking-wide text-muted">Parcel {home.pid}</p>
        <h2 className="text-2xl font-bold text-ink sm:text-3xl">{home.address}</h2>
        <p className="mt-1 text-copy">
          {[home.sqft && `${home.sqft.toLocaleString()} sq ft`, home.yearBuilt && `built ${home.yearBuilt}`,
            home.beds != null && `${home.beds} bed`, home.baths != null && `${home.baths} bath`,
            home.grade && `quality grade ${home.grade}`, home.condition && `${home.condition.toLowerCase()} condition`]
            .filter(Boolean).join(" · ")}
        </p>
      </div>

      <section className={`rounded-lg border-l-8 p-5 sm:p-6 ${TONE_CLASSES[v.tone]}`}>
        <h3 className="flex items-center gap-3 text-xl font-bold sm:text-2xl">
          <span aria-hidden>{v.icon}</span> {v.title}
        </h3>
        <p className="mt-2 text-ink">{v.summary}</p>
        {hasEstimate && chanceSentence(home.chance) && <p className="mt-2 text-sm text-copy">{chanceSentence(home.chance)}</p>}
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Stat label="County's 2026 value" value={money(home.value2026)}
          note={change != null ? `${pct(change, 1)} from ${money(home.value2025)} in 2025` : undefined} />
        <Stat label="Square Deal estimate" value={hasEstimate ? roundMoney(home.estimate) : "—"}
          note={gap != null ? `The county's value is ${Math.abs(Math.round(gap * 100))}% ${gap >= 0 ? "above" : "below"} this` : undefined} />
        <Stat label={showTax ? "Roughly, per year" : "Deadline to file"}
          value={showTax ? `${money(Math.round((home.yearlyTax ?? 0) / 10) * 10)} less tax` : DEADLINE}
          note={showTax ? "if the county used our estimate" : "Board of Revision, tax year 2026"} />
      </section>

      {hasEstimate && home.middleLow && home.middleHigh && home.low80 && home.high80 && home.value2026 && (
        <section className="rounded-lg border border-line bg-card p-5 sm:p-6">
          <h3 className="text-lg font-semibold">Where the county&apos;s value falls</h3>
          <RangeBar estimate={home.estimate!} middleLow={home.middleLow} middleHigh={home.middleHigh}
            low80={home.low80} high80={home.high80} county={home.value2026} />
          <p className="mt-3 text-sm text-copy">
            The estimate is what this home would most likely have sold for on January 1, 2026, the date the county&apos;s values
            are set for. It blends the five sales below with a model fitted to about 31,000 county sales. It is not an appraisal.
          </p>
        </section>
      )}

      {hasEstimate && (
        <section>
          <h3 className="text-lg font-semibold">The sales it&apos;s based on</h3>
          <p className="mt-1 text-sm text-copy">
            The most similar nearby sales from 2023 to 2025 that the county itself marked as valid market sales. Each price is
            restated to the January 2026 market, then adjusted for how the home differs from yours.
          </p>
          {error && <p className="mt-3 text-bad">Couldn&apos;t load the sales: {error}</p>}
          {!sales && !error && <p className="mt-3 text-muted">Loading the sales…</p>}
          {sales && <CompsTable home={home} sales={sales} />}
        </section>
      )}

      <section className="rounded-lg border border-line bg-card p-5 sm:p-6">
        <h3 className="text-lg font-semibold">What to do next</h3>
        <NextSteps home={home} />
        <div className="no-print mt-4 flex flex-wrap gap-3">
          <button type="button" onClick={() => window.print()}
            className="rounded-md border border-accent px-4 py-2 font-semibold text-accent hover:bg-accent-soft">
            Print this page
          </button>
          <Link href="/how-to-file/" className="rounded-md bg-accent px-4 py-2 font-semibold text-accent-ink hover:opacity-90">
            How to file a complaint
          </Link>
        </div>
      </section>
    </article>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg border border-line bg-card p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="tabular mt-1 text-2xl font-bold text-ink">{value}</p>
      {note && <p className="mt-1 text-sm text-copy">{note}</p>}
    </div>
  );
}

function CompsTable({ home, sales }: { home: Home; sales: Sale[] }) {
  const rows = home.comps.map((i, k) => ({ sale: sales[i], adjusted: home.adjusted[k] })).filter((r) => r.sale);
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-line bg-card">
      <table className="tabular w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-line text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Address</th>
            <th className="px-3 py-2 font-medium">Sold</th>
            <th className="px-3 py-2 text-right font-medium">Price</th>
            <th className="px-3 py-2 text-right font-medium">Size</th>
            <th className="px-3 py-2 text-right font-medium">Built</th>
            <th className="px-3 py-2 font-medium">Bed / bath</th>
            <th className="px-3 py-2 font-medium">Grade</th>
            <th className="px-3 py-2 text-right font-medium">Away</th>
            <th className="px-3 py-2 text-right font-medium">Adjusted to yours</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ sale: s, adjusted }, k) => (
            <tr key={k} className="border-b border-line last:border-0">
              <td className="px-3 py-2">{s.address.split(",")[0]}</td>
              <td className="px-3 py-2 whitespace-nowrap">{monthLabel(s.month)}</td>
              <td className="px-3 py-2 text-right">{money(s.price)}</td>
              <td className="px-3 py-2 text-right">{s.sqft?.toLocaleString()} sq ft</td>
              <td className="px-3 py-2 text-right">{s.yearBuilt}</td>
              <td className="px-3 py-2">{s.beds ?? "–"} / {s.baths ?? "–"}</td>
              <td className="px-3 py-2">{s.grade}</td>
              <td className="px-3 py-2 text-right whitespace-nowrap">
                {home.lat && home.lon ? `${miles([home.lat, home.lon], [s.lat, s.lon]).toFixed(1)} mi` : "–"}
              </td>
              <td className="px-3 py-2 text-right font-semibold">{money(adjusted)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NextSteps({ home }: { home: Home }) {
  const common = (
    <p className="mt-2 text-copy">
      Complaints for tax year 2026 are due by <strong>{DEADLINE}</strong>. Check the Auditor&apos;s Board of Revision page for the
      exact filing window. Filing is free.
    </p>
  );
  switch (home.verdict) {
    case "likely_high":
      return (
        <div className="prose-copy mt-2 text-copy">
          <p>
            Consider filing a complaint (DTE Form 1) with the Franklin County Board of Revision. Bring evidence of what your home was
            worth on January 1, 2026: the strongest is a recent sale of your own home or an appraisal; sales of similar homes nearby,
            like the ones above, and photos or repair estimates for problems also help.
          </p>
          {common}
        </div>
      );
    case "closer_look":
      return (
        <div className="prose-copy mt-2 text-copy">
          <p>
            Look at the sales above. Are they really like your home? Does your home have problems (a roof, foundation, or layout
            issue) that the county&apos;s record doesn&apos;t show? If the closest matches sold for less than your county value, or
            your home is in worse shape than its record says, a complaint may be worth it.
          </p>
          {common}
        </div>
      );
    case "low":
      return (
        <p className="mt-2 text-copy">
          Probably nothing. A complaint opens your value to review in both directions, and school districts can file to raise values
          too.
        </p>
      );
    case "in_line":
      return <p className="mt-2 text-copy">Probably nothing. If you know something about your home that the county doesn&apos;t, see how to file.</p>;
    default:
      return (
        <p className="mt-2 text-copy">
          Look up your home on the Franklin County Auditor&apos;s website and compare it with recent sales of similar homes nearby.
          {" "}Complaints for tax year 2026 are due by {DEADLINE}.
        </p>
      );
  }
}
