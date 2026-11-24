/**
 * Fill numbers (KAN-476), the /admin/fill-health page's pure half: the
 * shapes GET /admin/fill-health answers (backend app/schemas/fill_events.py)
 * and the page's filters. The read is in ./fill-report-queries.ts.
 */

export type FillHealthRow = {
  day: string;
  job_system: string;
  /** Fills, a Workday walk once (its final step's event). */
  fills: number;
  /** The share of pages (a Workday step is one) with no failed field: a job system that breaks shows as this dropping. */
  clean_share: number;
  /** Fields left needing the student over all fields, less those skipped by the student's choice. */
  needs_you_rate: number;
  top_errors: { name: string; count: number }[];
};

export type FillHealth = { rows: FillHealthRow[]; engine_versions: string[] };

type Param = string | string[] | undefined;
const first = (value: Param) => (Array.isArray(value) ? value[0] : value);

/** A plain engine version (letters, digits and . _ + -), or null. */
export function versionOf(value: Param): string | null {
  const version = first(value);
  return version && /^[A-Za-z0-9._+-]{1,64}$/.test(version) ? version : null;
}

/** A share as a whole percent: "67%". */
export function percent(share: number): string {
  return `${Math.round(share * 100)}%`;
}

/** The fills of some rows: all of them, and each job system's, most first. */
export function fillTotals(rows: FillHealthRow[]): {
  fills: number;
  systems: { job_system: string; fills: number }[];
} {
  const by = new Map<string, number>();
  for (const r of rows) by.set(r.job_system, (by.get(r.job_system) ?? 0) + r.fills);
  const systems = [...by].map(([job_system, fills]) => ({ job_system, fills }));
  systems.sort((x, y) => y.fills - x.fills || x.job_system.localeCompare(y.job_system));
  return { fills: systems.reduce((sum, s) => sum + s.fills, 0), systems };
}

/**
 * The Fills table's filters. `needsYou` is the lowest rate a row may have,
 * as a share ("0.25"). `errors` is "with" (any error), "none", or
 * "name:<error name>" for one error.
 */
export type FillFilters = { system: string; needsYou: string; errors: string };
export const ALL_FILLS = "all";
export const NO_FILL_FILTERS: FillFilters = {
  system: ALL_FILLS,
  needsYou: ALL_FILLS,
  errors: ALL_FILLS,
};

/** Whether a row passes every filter. */
export function matchesFilters(row: FillHealthRow, filters: FillFilters): boolean {
  const { system, needsYou, errors } = filters;
  if (system !== ALL_FILLS && row.job_system !== system) return false;
  if (needsYou !== ALL_FILLS && row.needs_you_rate < Number(needsYou)) return false;
  if (errors === "with") return row.top_errors.length > 0;
  if (errors === "none") return row.top_errors.length === 0;
  if (errors.startsWith("name:")) return row.top_errors.some((e) => `name:${e.name}` === errors);
  return true;
}

/** GET /admin/scrape-health's answer (KAN-879, backend app/routers/scrape_health.py). */
export type ScrapeHealth = {
  /** When the API read these numbers; it keeps them for 10 minutes. */
  read_at: string;
  /** The newest job posting write: the scheduled feed import's trace. */
  last_import_at: string | null;
  boards: {
    boards: number;
    failing: number;
    resting: number;
    stale: number;
    /** The backlog: tasks no worker has taken, and tasks a worker took and has not finished. */
    pending: number;
    claimed: number;
    oldest_pending_at: string | null;
  };
  /** Enabled boards per hiring system, and how many were ever read. */
  systems: { ats: string; boards: number; read: number; last_read_at: string | null }[];
  days: {
    day: string;
    ats: string;
    done: number;
    failed: number;
    mean_seconds: number | null;
    new_jobs: number;
  }[];
  failing: {
    ats: string;
    token: string;
    company: string;
    consecutive_failures: number;
    last_error: string | null;
  }[];
  /**
   * The failed reads by reason (the error's text before its first ": "),
   * most boards first, with the newest read's board and whole error.
   */
  errors: {
    reason: string;
    boards: number;
    reads: number;
    last_at: string;
    ats: string;
    token: string;
    company: string;
    error: string | null;
  }[];
};
