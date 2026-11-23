"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

import { HomeResult } from "./HomeResult";
import { loadStreet, loadStreets, matchStreets, parseAddress, type Home, type StreetEntry } from "@/lib/homes";

declare global {
  interface Window {
    goatcounter?: { count: (o: { path: string; title?: string; event?: boolean }) => void };
  }
}

/* Count that a lookup happened and its verdict, never the address. */
function track(path: string) {
  window.goatcounter?.count({ path, event: true });
}

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "pick"; homes: Home[]; note: string }
  | { kind: "result"; home: Home }
  | { kind: "none"; message: string };

export function HomeSearch() {
  const [query, setQuery] = useState("");
  const [streets, setStreets] = useState<StreetEntry[] | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [state, setState] = useState<State>({ kind: "idle" });
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const ensureStreets = () => {
    if (!streets) loadStreets().then(setStreets).catch(() => setState({ kind: "none", message: "Couldn't load the street list. Try reloading the page." }));
  };

  const parsed = useMemo(() => parseAddress(query), [query]);
  const suggestions = useMemo(
    () => (streets && parsed.street.length >= 2 ? matchStreets(streets, parsed.street, parsed.zip) : []),
    [streets, parsed],
  );
  useEffect(() => setActive(0), [query]);

  async function lookUp(entry: StreetEntry | undefined) {
    setOpen(false);
    if (!entry) {
      setState({ kind: "none", message: "We couldn't find that street in Franklin County's single-family homes. Check the spelling, or try just the house number and street name." });
      return;
    }
    if (parsed.number == null) {
      setState({ kind: "none", message: "Add the house number, like “1234 Main St”." });
      return;
    }
    setState({ kind: "loading" });
    try {
      const homes = (await loadStreet(entry)).filter((h) => h.number === parsed.number);
      const inZip = parsed.zip ? homes.filter((h) => h.address.endsWith(parsed.zip!)) : homes;
      const found = inZip.length ? inZip : homes;
      if (found.length === 1) {
        setState({ kind: "result", home: found[0] });
        track(`lookup/${found[0].verdict}`);
      } else if (found.length > 1) {
        setState({ kind: "pick", homes: found, note: "More than one home matches. Which one?" });
      } else {
        setState({
          kind: "none",
          message: `No single-family home at ${parsed.number} ${entry.street}. Square Deal covers single-family homes only, not condos, duplexes, or apartments.`,
        });
        track("lookup/not-found");
      }
    } catch {
      setState({ kind: "none", message: "Something went wrong loading that street. Try again." });
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    lookUp(suggestions[active] ?? suggestions[0]);
  }

  function onKey(e: React.KeyboardEvent) {
    if (!open || !suggestions.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, suggestions.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    if (e.key === "Escape") setOpen(false);
  }

  return (
    <div>
      <form onSubmit={submit} className="relative no-print" role="search">
        <label htmlFor="address" className="block text-lg font-semibold text-ink">
          Your home&apos;s address
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            id="address" ref={inputRef} value={query} autoComplete="off" spellCheck={false}
            placeholder="e.g. 1234 Main St, Columbus 43215"
            onFocus={() => { ensureStreets(); setOpen(true); }}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); ensureStreets(); }}
            onKeyDown={onKey}
            role="combobox" aria-expanded={open && suggestions.length > 0} aria-controls={listId} aria-autocomplete="list"
            aria-activedescendant={open && suggestions.length ? `${listId}-${active}` : undefined}
            className="w-full rounded-md border-2 border-line bg-card px-4 py-3 text-lg text-ink placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <button type="submit" className="rounded-md bg-accent px-6 py-3 text-lg font-semibold text-accent-ink hover:opacity-90">
            Check
          </button>
        </div>
        {open && suggestions.length > 0 && (
          <ul id={listId} role="listbox" className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-line bg-card shadow-lg sm:w-[calc(100%-7rem)]">
            {suggestions.map((s, i) => (
              <li key={s.street} id={`${listId}-${i}`} role="option" aria-selected={i === active}
                onMouseDown={(e) => { e.preventDefault(); lookUp(s); }}
                onMouseEnter={() => setActive(i)}
                className={`cursor-pointer px-4 py-2 ${i === active ? "bg-accent-soft" : ""}`}>
                <span className="font-medium text-ink">{parsed.number ? `${parsed.number} ` : ""}{s.street}</span>
                <span className="ml-2 text-sm text-muted">{s.cities.slice(0, 3).join(", ")}{s.zips.length ? ` · ${s.zips.slice(0, 3).join(", ")}` : ""}</span>
              </li>
            ))}
          </ul>
        )}
        {!streets && open && query.length > 2 && <p className="mt-2 text-sm text-muted">Loading streets…</p>}
      </form>

      {state.kind === "loading" && <p className="mt-6 text-muted">Looking up the home…</p>}
      {state.kind === "none" && <p className="rise mt-6 rounded-md border border-line bg-card p-4 text-copy">{state.message}</p>}
      {state.kind === "pick" && (
        <div className="rise mt-6 rounded-md border border-line bg-card p-4">
          <p className="font-semibold text-ink">{state.note}</p>
          <ul className="mt-2 space-y-1">
            {state.homes.map((h) => (
              <li key={h.pid}>
                <button type="button" className="text-accent underline underline-offset-4"
                  onClick={() => { setState({ kind: "result", home: h }); track(`lookup/${h.verdict}`); }}>
                  {h.address} (parcel {h.pid})
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {state.kind === "result" && <HomeResult home={state.home} />}
    </div>
  );
}
