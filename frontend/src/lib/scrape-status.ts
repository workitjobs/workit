/**
 * Scrape Health's pure half (KAN-879): the page's window in the last 90
 * days, the status rule, and a hiring system's name. The shapes are in
 * ./fill-health.ts; the read is in ./fill-report-queries.ts.
 */

import type { ScrapeHealth } from "@/lib/fill-health";

const DAY = 86_400_000;

/** The most days GET /admin/scrape-health answers: how far back the page reads. */
export const HISTORY = 90;
/** The periods the page offers, in days. */
export const SPANS = [7, 14, 30, 90] as const;

type Param = string | string[] | undefined;
const first = (value: Param) => (Array.isArray(value) ? value[0] : value);
const whole = (value: Param) => Number.parseInt(first(value) ?? "", 10);

/**
 * The days the page shows: a period that ends today (UTC). It is the page's
 * one time setting (KAN-953). It also had a distance back from today, moved
 * by two arrows beside the period: every day the arrows reached, the 90-day
 * period already showed, the forward arrow was off on every first visit,
 * and the control took 520px of the title row, so the arrows went
 * (2026-11-27). Before that the arrows had a switch of their own, Move By
 * (week or month), which the user found made no sense beside the periods
 * (2026-11-22).
 */
export type Window = {
  /** How many days show: the period. */
  days: number;
};

/**
 * The window a page address asks for: `days` is one of SPANS, else 14. Any
 * other key is ignored, so an address from before (`back`, `step`) still
 * opens, on the days that end today.
 */
export function windowOf(params: { days?: Param }): Window {
  const asked = whole(params.days);
  return { days: (SPANS as readonly number[]).includes(asked) ? asked : 14 };
}

/**
 * A page's address for a window. `path` is the admin page (every admin page
 * shares the time control), and `keep` the page's other filters, each left
 * out when empty.
 */
export function windowHref(
  window: Window,
  path = "/admin/scrape-health",
  keep: Record<string, string> = {},
): string {
  const query = new URLSearchParams({ days: String(window.days) });
  for (const [key, value] of Object.entries(keep)) if (value) query.set(key, value);
  return `${path}?${query}`;
}

/** The window's days as ISO dates (UTC), oldest first. `today` is YYYY-MM-DD. */
export function datesOf(window: Window, today: string): string[] {
  const end = Date.parse(`${today}T00:00:00Z`);
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
