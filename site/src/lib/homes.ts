/* Loading and searching the precomputed results in public/data (written by scripts/export_site.py). */

export const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export type Verdict = "no_estimate" | "in_line" | "closer_look" | "likely_high" | "low";
const VERDICTS: Verdict[] = ["no_estimate", "in_line", "closer_look", "likely_high", "low"];

export type Home = {
  number: number | null;
  address: string;
  pid: string;
  value2025: number | null;
  value2026: number | null;
  estimate: number | null;
  middleLow: number | null;
  middleHigh: number | null;
  low80: number | null;
  high80: number | null;
  verdict: Verdict;
  yearlyTax: number | null;
  sqft: number | null;
  yearBuilt: number | null;
  beds: number | null;
  baths: number | null;
  grade: string;
  condition: string;
  acres: number | null;
  lat: number | null;
  lon: number | null;
  comps: number[];
  adjusted: (number | null)[];
  /* share of homes like this one that sold for less than their county value in 2026 */
  chance: number | null;
};

export type Sale = {
  address: string;
  month: string;
  price: number;
  priceJan2026: number;
  sqft: number;
  yearBuilt: number;
  beds: number | null;
  baths: number | null;
  grade: string;
  condition: string;
  lat: number;
  lon: number;
};

type Row = [number | null, string, string, ...unknown[]];
export type StreetEntry = { street: string; shard: number; zips: string[]; cities: string[]; canonical?: string };

export function parseHome(r: unknown[]): Home {
  const n = (i: number) => (r[i] as number | null) ?? null;
  return {
    number: n(0), address: r[1] as string, pid: r[2] as string,
    value2025: n(3), value2026: n(4), estimate: n(5), middleLow: n(6), middleHigh: n(7), low80: n(8), high80: n(9),
    verdict: VERDICTS[r[10] as number] ?? "no_estimate", yearlyTax: n(11),
    sqft: n(12), yearBuilt: n(13), beds: n(14), baths: n(15), grade: (r[16] as string) || "", condition: (r[17] as string) || "",
    acres: n(18), lat: n(19), lon: n(20), comps: (r[21] as number[]) ?? [], adjusted: (r[22] as (number | null)[]) ?? [],
    chance: (r[23] as number | null) ?? null,
  };
}

const cache = new Map<string, Promise<unknown>>();
function getJSON<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(`${BASE}/data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`Couldn't load ${path} (${r.status})`);
      return r.json();
    }));
  }
  return cache.get(path) as Promise<T>;
}

export async function loadStreets(): Promise<StreetEntry[]> {
  const raw = await getJSON<[string, number, string[], string[]][]>("streets.json");
  return raw.map(([street, shard, zips, cities]) => ({ street, shard, zips, cities }));
}

export async function loadStreet(entry: StreetEntry): Promise<Home[]> {
  const shard = await getJSON<Record<string, Row[]>>(`homes/${entry.shard}.json`);
  return (shard[entry.street] ?? []).map(parseHome);
}

export async function loadSales(): Promise<Sale[]> {
  const raw = await getJSON<{ rows: unknown[][] }>("sales.json");
  return raw.rows.map((r) => ({
    address: r[0] as string, month: r[1] as string, price: r[2] as number, priceJan2026: r[3] as number,
    sqft: r[4] as number, yearBuilt: r[5] as number, beds: r[6] as number | null, baths: r[7] as number | null,
    grade: r[8] as string, condition: r[9] as string, lat: r[10] as number, lon: r[11] as number,
  }));
}

/* ── Address parsing ──────────────────────────────────────────────────────────────────────────────── */

/* Street types, every spelling -> one canonical form. The county uses its own short forms (WY, BL, CR, PW, TE...),
   so both the county's street names and what people type are put through the same function. */
const SUFFIX_GROUPS: [string, string[]][] = [
  ["ST", ["STREET", "STR"]], ["AVE", ["AVENUE", "AV"]], ["RD", ["ROAD"]], ["DR", ["DRIVE"]], ["CT", ["COURT"]],
  ["LN", ["LANE"]], ["PL", ["PLACE"]], ["WAY", ["WY"]], ["BLVD", ["BOULEVARD", "BL"]], ["CIR", ["CIRCLE", "CR"]],
  ["SQ", ["SQUARE"]], ["LOOP", ["LP"]], ["PIKE", ["PK"]], ["ALY", ["ALLEY", "AL"]], ["TRL", ["TRAIL", "TR"]],
  ["PKWY", ["PARKWAY", "PW"]], ["TER", ["TERRACE", "TE"]], ["XING", ["CROSSING"]], ["BEND", ["BND"]],
  ["RIDGE", ["RDG"]], ["GREEN", ["GRN"]], ["HWY", ["HIGHWAY"]], ["COVE", ["CV"]], ["GLEN", ["GLN"]], ["PT", ["POINT"]],
  ["TRCE", ["TRACE"]], ["HTS", ["HEIGHTS"]], ["VW", ["VIEW"]],
];
const SUFFIX: Record<string, string> = Object.fromEntries(
  SUFFIX_GROUPS.flatMap(([canon, alts]) => [[canon, canon], ...alts.map((a) => [a, canon])]),
);
const DIRECTION: Record<string, string> = {
  NORTH: "N", SOUTH: "S", EAST: "E", WEST: "W", NORTHEAST: "NE", NORTHWEST: "NW", SOUTHEAST: "SE", SOUTHWEST: "SW",
  N: "N", S: "S", E: "E", W: "W", NE: "NE", NW: "NW", SE: "SE", SW: "SW",
};

export function canonicalStreet(s: string): string {
  const w = s.toUpperCase().replace(/[.,#']/g, " ").split(/\s+/).filter(Boolean);
  if (w.length > 1 && DIRECTION[w[0]]) w[0] = DIRECTION[w[0]];
  let last = w.length - 1;
  if (last > 0 && DIRECTION[w[last]]) {
    w[last] = DIRECTION[w[last]];
    last -= 1;
  }
  if (last > 0 && SUFFIX[w[last]]) w[last] = SUFFIX[w[last]];
  return w.join(" ");
}

export type ParsedAddress = { number: number | null; street: string; zip: string | null };

/* "123 W. Main Street, Columbus, OH 43215" -> {number: 123, street: "W MAIN ST", zip: "43215"} */
export function parseAddress(input: string): ParsedAddress {
  const zip = input.match(/\b(43\d{3})\b/)?.[1] ?? null;
  let s = input.toUpperCase().replace(/\b43\d{3}(-\d{4})?\b/, "");
  s = s.split(",")[0];
  s = s.replace(/\b(OH|OHIO)\b\s*$/, "");
  const m = s.trim().match(/^(\d+)\s*(?:-\s*\d+)?\s+(.*)$/);
  const number = m ? parseInt(m[1], 10) : null;
  const rest = (m ? m[2] : s).replace(/\b(APT|UNIT|STE|#)\s*\S+$/, "");
  return { number, street: canonicalStreet(rest), zip };
}

/* Best street matches for what someone typed (already canonical), exact first. */
export function matchStreets(streets: StreetEntry[], typed: string, zip: string | null, limit = 8): StreetEntry[] {
  if (!typed) return [];
  const words = typed.split(" ");
  const scored: [number, StreetEntry][] = [];
  for (const e of streets) {
    const c = e.canonical ?? (e.canonical = canonicalStreet(e.street));
    let score = -1;
    if (c === typed) score = 0;
    else if (c.startsWith(typed)) score = 1;
    else if (words.every((w) => c.split(" ").some((p) => p.startsWith(w)))) score = 2;
    if (score < 0) continue;
    if (zip && !e.zips.includes(zip)) score += 3;
    scored.push([score, e]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].street.length - b[1].street.length || a[1].street.localeCompare(b[1].street));
  return scored.slice(0, limit).map(([, e]) => e);
}

/* ── Formatting ───────────────────────────────────────────────────────────────────────────────────── */

export const money = (x: number | null | undefined) =>
  x == null ? "—" : x.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const roundMoney = (x: number | null | undefined, to = 1000) => (x == null ? "—" : money(Math.round(x / to) * to));

export function pct(x: number, digits = 0) {
  return `${x >= 0 ? "+" : "−"}${Math.abs(x * 100).toFixed(digits)}%`;
}

export function monthLabel(m: string) {
  const [y, mo] = m.split("-").map(Number);
  return new Date(y, mo - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

/* Distance in miles between two points. */
export function miles(a: [number, number], b: [number, number]) {
  const R = 3958.8;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b[0] - a[0]);
  const dLon = toRad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
