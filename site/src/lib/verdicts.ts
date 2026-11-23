import type { Verdict } from "./homes";
import validation from "../../public/data/validation.json";

const base = Math.round(validation.base_rate_check_half.sold_below_county_value * 10);

export type Tone = "ok" | "warn" | "bad" | "info" | "neutral";

export const VERDICT: Record<Verdict, { title: string; tone: Tone; icon: string; summary: string }> = {
  likely_high: {
    title: "Your value may be too high",
    tone: "bad",
    icon: "▲",
    summary:
      "The county's 2026 value is above what similar homes nearby support, by enough that homes like this one often sold for less than their county value. That's what a Board of Revision complaint is for, and the sales below are the kind of evidence it asks for.",
  },
  closer_look: {
    title: "Worth a closer look",
    tone: "warn",
    icon: "◆",
    summary:
      "The county's value is above our estimate. Check the sales below: if the closest matches sold for less, or your home has problems the county's record doesn't show, you may have a case.",
  },
  in_line: {
    title: "Your value looks in line",
    tone: "ok",
    icon: "✓",
    summary:
      "The county's value is about what similar homes nearby support. A complaint probably wouldn't lower it.",
  },
  low: {
    title: "Your value looks low",
    tone: "info",
    icon: "▼",
    summary:
      "The county's value is below what similar homes nearby sold for. The Board of Revision can raise a value as well as lower it, so filing probably isn't in your interest.",
  },
  no_estimate: {
    title: "We can't estimate this home",
    tone: "neutral",
    icon: "–",
    summary:
      "Square Deal covers single-family homes with one building and complete records, near enough recent sales to compare. This one is outside that: it may have more than one building, an unusual size, missing details, or too few sales nearby.",
  },
};

/* "Of homes like yours, about 6 in 10 sold for less than their county value (about 2 in 10 for all homes)." */
export function chanceSentence(chance: number | null): string | null {
  if (chance == null) return null;
  const k = Math.max(1, Math.min(9, Math.round(chance * 10)));
  return `In 2026, about ${k} in 10 homes with a gap like yours between the county's value and similar sales sold for less than their county value. Across all homes it was about ${base} in 10.`;
}

export const TONE_CLASSES: Record<Tone, string> = {
  ok: "border-ok bg-ok-soft text-ok",
  warn: "border-warn bg-warn-soft text-warn",
  bad: "border-bad bg-bad-soft text-bad",
  info: "border-info bg-info-soft text-info",
  neutral: "border-line bg-card text-muted",
};
