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

type Param = string | string[] | undefined;
const first = (value: Param) => (Array.isArray(value) ? value[0] : value);
const whole = (value: Param) => Number.parseInt(first(value) ?? "", 10);

/**
 * The days the page shows: a period, and how far back from today it ends.
 * The period is also the arrows' step, so the page has one time control.
 * It had a second one, Move By (week or month), for the arrows alone: beside
 * the periods it read as a second way to pick a length of time, and the user
 * found the two made no sense together (2026-11-22).
 */
export type Window = {
  /** How many days show: the period. */
  days: number;
  /** Days between the window's last day and today. */
  back: number;
};

/**
 * The window a page address asks for. `days` is one of SPANS (else 14), and
 * `back` is cut to what HISTORY leaves. Any other key is ignored.
 */
export function windowOf(params: { days?: Param; back?: Param }): Window {
  const asked = whole(params.days);
  const days = (SPANS as readonly number[]).includes(asked) ? asked : 14;
  const back = Math.max(0, Math.min(HISTORY - days, whole(params.back) || 0));
  return { days, back };
}

/**
 * A page's address for a window, leaving out a zero `back`. `path` is the
 * admin page (Fill Health shares the time control), and `keep` the page's
 * other filters, each left out when empty.
 */
export function windowHref(
  window: Window,
  path = "/admin/scrape-health",
  keep: Record<string, string> = {},
): string {
  const query = new URLSearchParams({ days: String(window.days) });
  if (window.back) query.set("back", String(window.back));
  for (const [key, value] of Object.entries(keep)) if (value) query.set(key, value);
  return `${path}?${query}`;
}

/**
 * The window moved one period: `by` is -1 for the period before (older), 1
 * for the period after (newer). Null where it cannot move.
 *
 * HISTORY is rarely a whole number of periods (90 days hold six periods of
 * 14 and 6 days more), so the last step back is cut to the days that are
 * left, and shows them with part of the period before. A step forward first
 * returns to a whole number of periods, so the way forward shows the same
 * windows as the way back did.
 */
export function moved(window: Window, by: -1 | 1): Window | null {
  const { days, back } = window;
  const cut = back % days;
  const to = by === -1 ? Math.min(HISTORY - days, back + days) : back - (cut || days);
  return to === back || to < 0 ? null : { days, back: to };
}

/**
 * The window with another period. Its last day stays where it was, so a
 * longer period shows more days before the ones in view, cut to what
 * HISTORY holds: the address then says the window as it will open.
 */
export function resized(window: Window, days: number): Window {
  return { days, back: Math.min(window.back, HISTORY - days) };
}

/** The window's days as ISO dates (UTC), oldest first. `today` is YYYY-MM-DD. */
export function datesOf(window: Window, today: string): string[] {
  const end = Date.parse(`${today}T00:00:00Z`) - window.back * DAY;
  return Array.from({ length: window.days }, (_, i) =>
    new Date(end - (window.days - 1 - i) * DAY).toISOString().slice(0, 10),
  );
}

const dayName = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

/** A day in words, "Nov 9", from its ISO date (UTC). */
export function dayLabel(date: string): string {
  return dayName.format(Date.parse(`${date}T00:00:00Z`));
}

/** The days a list of dates spans, in words: "Nov 9 to Nov 22". */
export function rangeOf(dates: string[]): string {
  return `${dayLabel(dates[0])} to ${dayLabel(dates[dates.length - 1])}`;
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
  return {
    level: "green",
    title: "Healthy",
    reason: "Boards are being read, and few are failing.",
  };
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
