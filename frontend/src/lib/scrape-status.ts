/**
 * Scrape Health's pure half (KAN-879): the page's window in the last 90
 * days, the status rule, and a hiring system's name. The shapes are in
 * ./fill-health.ts; the read is in ./fill-report-queries.ts.
 */

import type { ScrapeHealth } from "@/lib/fill-health";

const DAY = 86_400_000;

/** The most days GET /admin/scrape-health answers: how far back the page reads and moves. */
export const HISTORY = 90;
/** The periods the page offers, in days. */
export const SPANS = [7, 14, 30, 90] as const;
export const STEPS = { week: 7, month: 30 } as const;
export type Step = keyof typeof STEPS;

type Param = string | string[] | undefined;
const first = (value: Param) => (Array.isArray(value) ? value[0] : value);
const whole = (value: Param) => Number.parseInt(first(value) ?? "", 10);

export type Window = {
  /** How many days show. */
  days: number;
  /** Days between the window's last day and today. */
  back: number;
  step: Step;
};

/**
 * The window a page address asks for. `days` is one of SPANS (else 14),
 * `back` is cut to what HISTORY leaves, and `step` is week or month (else a
 * week for the two short periods and a month for the two long ones).
 */
export function windowOf(params: { days?: Param; back?: Param; step?: Param }): Window {
  const asked = whole(params.days);
  const days = (SPANS as readonly number[]).includes(asked) ? asked : 14;
  const back = Math.max(0, Math.min(HISTORY - days, whole(params.back) || 0));
  const named = first(params.step);
  const step: Step = named === "week" || named === "month" ? named : days <= 14 ? "week" : "month";
  return { days, back, step };
}

/** The page's address for a window, leaving out what is the default. */
export function windowHref(window: Window): string {
  const query = new URLSearchParams({ days: String(window.days) });
  if (window.back) query.set("back", String(window.back));
  if (window.step !== (window.days <= 14 ? "week" : "month")) query.set("step", window.step);
  return `/admin/scrape-health?${query}`;
}

/** The window moved by its step: `by` is -1 for older, 1 for newer. Null where it cannot move. */
export function moved(window: Window, by: -1 | 1): Window | null {
  const back = window.back - by * STEPS[window.step];
  const cut = Math.max(0, Math.min(HISTORY - window.days, back));
  return cut === window.back ? null : { ...window, back: cut };
}

/** The window's days as ISO dates (UTC), oldest first. `today` is YYYY-MM-DD. */
export function datesOf(window: Window, today: string): string[] {
  const end = Date.parse(`${today}T00:00:00Z`) - window.back * DAY;
  return Array.from({ length: window.days }, (_, i) =>
    new Date(end - (window.days - 1 - i) * DAY).toISOString().slice(0, 10),
  );
}

/** A board is not being read once the newest read is this old. */
export const RED_AFTER_HOURS = 24;
/** The share of enabled boards failing that needs a look. */
export const AMBER_FAILING_SHARE = 0.05;

export type Status = { level: "red" | "amber" | "green"; title: string; reason: string };

/**
 * The page's one answer, by the rules the team set (KAN-879): red when no
 * board was read in RED_AFTER_HOURS, amber when more than
 * AMBER_FAILING_SHARE of the boards are failing, else green. `now` is a
 * time in milliseconds.
 */
export function statusOf(data: Pick<ScrapeHealth, "boards" | "systems">, now: number): Status {
  const reads = data.systems.flatMap((s) => (s.last_read_at ? [Date.parse(s.last_read_at)] : []));
  if (reads.length === 0) {
    return { level: "red", title: "Not Running", reason: "No board was ever read." };
  }
  const newest = Math.max(...reads);
  const hours = Math.floor((now - newest) / 3_600_000);
  if (hours >= RED_AFTER_HOURS) {
    const ago = hours >= 48 ? `${Math.floor(hours / 24)} days` : `${hours} hours`;
    return {
      level: "red",
      title: "Not Running",
      reason: `No board was read in the last ${RED_AFTER_HOURS} hours. The newest read was ${ago} ago.`,
    };
  }
  const { boards, failing } = data.boards;
  if (boards > 0 && failing / boards > AMBER_FAILING_SHARE) {
    return {
      level: "amber",
      title: "Needs Attention",
      reason: `${failing} of ${boards} boards are failing, more than ${AMBER_FAILING_SHARE * 100}%.`,
    };
  }
  return { level: "green", title: "Healthy", reason: "Boards are being read, and few are failing." };
}

/** The names the scraper's ids cannot be capitalised into. */
const NAMES: Record<string, string> = {
  icims: "iCIMS",
  tiktok: "TikTok",
  successfactors: "SuccessFactors",
  bamboohr: "BambooHR",
};

/** A hiring system's name from the scraper's id: "iCIMS", "Workday". */
export function systemName(ats: string): string {
  return NAMES[ats] ?? ats.charAt(0).toUpperCase() + ats.slice(1);
}
