import { roundMoney } from "@/lib/homes";

/* One line: the wide 80% band, the middle half, our estimate, and the county's value. */
export function RangeBar({ estimate, middleLow, middleHigh, low80, high80, county }: {
  estimate: number; middleLow: number; middleHigh: number; low80: number; high80: number; county: number;
}) {
  const lo = Math.min(low80, county) * 0.97;
  const hi = Math.max(high80, county) * 1.03;
  const at = (x: number) => `${((x - lo) / (hi - lo)) * 100}%`;
  const countyLeft = (county - lo) / (hi - lo);
  return (
    <figure className="mt-2">
      <div className="relative h-24" role="img"
        aria-label={`Our estimate is ${roundMoney(estimate)}. Half of similar homes would sell between ${roundMoney(middleLow)} and ${roundMoney(middleHigh)}; most between ${roundMoney(low80)} and ${roundMoney(high80)}. The county's 2026 value is ${roundMoney(county)}.`}>
        {/* county value label above */}
        <div className="absolute top-0 whitespace-nowrap text-sm font-semibold text-ink"
          style={{ left: at(county), transform: `translateX(${countyLeft > 0.8 ? "-90%" : countyLeft < 0.2 ? "-10%" : "-50%"})` }}>
          County: {roundMoney(county)}
        </div>
        <div className="absolute top-6 h-4 w-0.5 bg-ink" style={{ left: at(county) }} />
        {/* track */}
        <div className="absolute top-10 h-5 w-full rounded-full bg-line/60" />
        <div className="absolute top-10 h-5 rounded-full bg-band" style={{ left: at(low80), width: `calc(${at(high80)} - ${at(low80)})` }} />
        <div className="absolute top-10 h-5 bg-band-strong" style={{ left: at(middleLow), width: `calc(${at(middleHigh)} - ${at(middleLow)})` }} />
        <div className="absolute top-8 h-9 w-1 -translate-x-1/2 rounded bg-accent" style={{ left: at(estimate) }} />
        <div className="absolute top-10 h-5 w-0.5 bg-ink" style={{ left: at(county) }} />
        {/* estimate label below */}
        <div className="absolute top-[4.6rem] -translate-x-1/2 whitespace-nowrap text-sm text-accent" style={{ left: at(estimate) }}>
          Our estimate: <span className="font-semibold">{roundMoney(estimate)}</span>
        </div>
      </div>
      <figcaption className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
        <span className="flex items-center gap-2"><span className="inline-block h-3 w-5 bg-band-strong" /> Half of similar homes: {roundMoney(middleLow)}–{roundMoney(middleHigh)}</span>
        <span className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm bg-band" /> Most (80%): {roundMoney(low80)}–{roundMoney(high80)}</span>
      </figcaption>
    </figure>
  );
}
