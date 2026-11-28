/**
 * Resume reading for admins (KAN-953), the /admin/resume-reading page's pure
 * half: the shape GET /admin/resume-reading answers (backend
 * app/routers/resume_reading.py), what each reason and route is called, the
 * page's status rule and its sums. The read is in ./fill-report-queries.ts.
 */

export type RecentReading = {
  at: string;
  /** The student's account id: the one thing on the page that names a student. */
  account: string;
  route: string;
  read_by: "model" | "parser";
  /** The model that replied; null when none did, and on rows from before the log held it. */
  model: string | null;
  /** Why the rule-based parser's reading was saved; null for the model's. */
  reason: string | null;
  seconds: number;
  entries: number;
  skills: number;
  tokens: number | null;
};

export type ModelReadings = {
  /** Null: model readings logged before the model's name was. */
  model: string | null;
  readings: number;
  median_seconds: number | null;
  input_tokens: number;
  output_tokens: number;
  /** The tokens at the model's paid price, in dollars; null when no price is set for it. */
  cost: number | null;
};

export type ScoringRun = {
  ran: string;
  /** "made_up" for the committed scoring set, "real" for the private one. */
  set: string;
  resumes: number;
  model: string;
  /** The share of the answer keys' fields each reading got right, in percent. */
  parser: number;
  ai: number;
  combined: number;
};

export type ReadingHealth = {
  read_at: string;
  /** Every student's AI readings today (UTC), and the day's limit. */
  today: { used: number; cap: number };
  /** Each day with a reading: how many the model read and how many the rule-based parser read. */
  days: { day: string; ai: number; parser: number }[];
  /** Why the rule-based parser's reading was saved, most first. */
  reasons: { reason: string; readings: number; last_at: string }[];
  /** The median time of a reading the model made. */
  median_seconds: number | null;
  models: ModelReadings[];
  accuracy: ScoringRun | null;
  /** The newest readings, newest first. */
  recent: RecentReading[];
};

/**
 * What each reason the log holds is called, and whether it is a model's
 * failure (`fault`) or by design: the daily limit and a file with no text
 * are WorkIt working as built, so they are grey where a failure is red.
 * The keys are the backend's PARSER_REASONS (models/resume_readings.py).
 */
const REASONS: Record<string, { label: string; fault: boolean }> = {
  // The student's own daily reading is used, or every student's daily pool is.
  no_uses_left: { label: "Daily Limit Reached", fault: false },
  model_unavailable: { label: "Model Unavailable", fault: true },
  timeout: { label: "Model Too Slow", fault: true },
  wrong_shape: { label: "Wrong Reply Shape", fault: true },
  nothing_backed: { label: "Nothing Backed by the Text", fault: true },
  no_text: { label: "No Text in the File", fault: false },
};

/** A reason's name and kind. One the page does not know yet shows as its key, and counts as no failure. */
export function reasonOf(reason: string): { label: string; fault: boolean } {
  return REASONS[reason] ?? { label: reason, fault: false };
}

const ROUTES: Record<string, string> = {
  upload: "Upload",
  preview: "Preview",
  update: "Import Updated Resume",
  import_again: "Import Again",
};

/** A route's name on the page; one the page does not know yet shows as its key. */
export function routeName(route: string): string {
  return ROUTES[route] ?? route;
}

/** A part of a whole as a whole percent: "83%". A dash when there is no whole. */
export function share(part: number, whole: number): string {
  return whole === 0 ? "–" : `${Math.round((part / whole) * 100)}%`;
}

/** Dollars as the page prints them: "$0.37". Under a cent keeps four places, so a small cost is not "$0.00". */
export function dollars(cost: number): string {
  return cost > 0 && cost < 0.01 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`;
}

/** The window's readings by reader, and all of them. */
export function readingTotals(days: ReadingHealth["days"]): {
  ai: number;
  parser: number;
  all: number;
} {
  const ai = days.reduce((sum, d) => sum + d.ai, 0);
  const parser = days.reduce((sum, d) => sum + d.parser, 0);
  return { ai, parser, all: ai + parser };
}

/** The readings where a model was asked and failed. */
export function faults(reasons: ReadingHealth["reasons"]): number {
  return reasons.reduce((sum, r) => sum + (reasonOf(r.reason).fault ? r.readings : 0), 0);
}

/** The newest readings that asked a model which the red rule looks at, and how many it needs. */
const LATEST = 5;
/** The share of asked readings a model may fail before the page is amber. */
const FAULT_SHARE = 0.1;

export type Status = {
  /** `none`: no reading in the period, so there is nothing to judge. */
  level: "green" | "amber" | "red" | "none";
  title: string;
  reason: string;
};

/**
 * The page's one answer: are models reading resumes?
 *
 * - RED when the newest `LATEST` readings that asked a model all failed: no
 *   model is answering now, whatever the period's sums say.
 * - AMBER when today's limit is reached (every upload until midnight UTC
 *   gets the rule-based parser's reading), or a model failed on more than
 *   `FAULT_SHARE` of the period's readings that asked one.
 * - GREEN otherwise.
 *
 * A reading "asked a model" when the model read it or a model failed on it.
 * One the daily limit or an empty file sent to the rule-based parser asked
 * none, so it never counts against the models.
 */
export function statusOf(health: ReadingHealth): Status {
  const { ai, all } = readingTotals(health.days);
  if (all === 0) {
    return { level: "none", title: "No Readings", reason: "No resume was read in this period." };
  }
  const asked = health.recent.filter(
    (r) => r.read_by === "model" || (r.reason !== null && reasonOf(r.reason).fault),
  );
  const latest = asked.slice(0, LATEST);
  if (latest.length === LATEST && latest.every((r) => r.read_by !== "model")) {
    return {
      level: "red",
      title: "AI Is Not Reading",
      reason: `No model replied to the last ${LATEST} readings that asked one. Students are getting the rule-based parser's reading.`,
    };
  }
  if (health.today.used >= health.today.cap) {
    return {
      level: "amber",
      title: "Needs Attention",
      reason:
        "Today's limit is reached. Every upload gets the rule-based parser's reading until midnight UTC.",
    };
  }
  const failed = faults(health.reasons);
  if (failed > (ai + failed) * FAULT_SHARE) {
    return {
      level: "amber",
      title: "Needs Attention",
      reason: `A model failed on ${share(failed, ai + failed)} of the readings that asked one in this period.`,
    };
  }
  return {
    level: "green",
    title: "Healthy",
    reason: "Models are answering, and today's limit is not reached.",
  };
}

/** A scoring run's resumes in words: "19 made-up resumes". */
export function scoredOn(run: ScoringRun): string {
  const kind = run.set === "real" ? "real" : "made-up";
  return `${run.resumes} ${kind} ${run.resumes === 1 ? "resume" : "resumes"}`;
}
