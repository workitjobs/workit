// What Apply sends the window: `Dashboard.state()` in apply/dashboard.py, each
// tile and item already through `verdict()`. Only the fields this window reads.

export type Tone = "idle" | "filling" | "verifying" | "ready" | "submitted" | "needs" | "failed" | "ended";

export type Choice = { kind?: "single" | "multi_select" | "file"; options: string[] };

export type Shown = {
  id?: string | number;
  tone: Tone;
  kind?: string; // a WORDS key: "missing fact", "held", "check", "needs sign-in", "needs code", "captcha", "blocked", "handoff"...
  label?: string;
  do?: string;
  why?: string;
  then?: string;
  company?: string;
  role?: string;
  posting_url?: string;
  link?: string; // the link the run was given (the queue's url), when it differs from the form's posting_url
  system?: string; // the job system: Greenhouse, Workday...
  company_domain?: string; // the logo's sources, from the WorkIt job posting when Apply has one (logo.ts)
  logo_url?: string;
  worker?: number;
  at?: string;
  from?: string; // "tracker": an Application from an earlier run
  live?: boolean; // a form still filling that asks its questions now
  answered?: boolean; // resolved in the window: it waits on the student no more
  // A tile's page Apply holds, so /fill-again fills it anew: Ask Claude's (askable), one whose session ended
  // (refill), or any held once its fill stopped (again).
  askable?: boolean;
  refill?: boolean;
  again?: boolean;
  application_id?: string;
  questions?: string[];
  choices?: Record<string, Choice>;
  required?: Record<string, boolean>;
  planned?: Record<string, string>;
  essays?: { question: string; text: string }[];
  written?: { name: string; label: string }[]; // each answer the AI wrote on the form, marked there (regenerate.form_of)
  flags?: { field: string; why: string }[];
  verified?: boolean; // the Pre-submit check found every answer agrees with the profile
  files?: { label?: string; name?: string }[]; // each file the form was given, by the form's question for it
  filled?: number;
  asked?: number;
  status?: string;
};

// What names a queued job, one shape wherever it shows (dashboard.QUEUED_JOB): its WorkIt job's company and title
// and its logo's sources. The queue lists it by `url` (bridge.Queued); a run names it by `link` while it waits to
// start, where a pasted link has its link alone.
export type QueuedJob = { company?: string; title?: string; logo_url?: string | null; company_domain?: string | null };

export type Waiting = QueuedJob & { link: string };

export type ApplyState = {
  tiles: Shown[];
  items: Shown[];
  run?: Run;
  context?: Record<string, unknown>;
};

// The run as a whole.
export type Run = {
  mode?: string; // "rehearsal" while a run goes; none on the idle board
  queued?: number;
  waiting?: Waiting[]; // the links not started yet, named as the queue named them
  paused?: boolean; // paused until a usage limit resets
  reason?: string; // why it's paused: "usage cap"
  paused_until?: string | null; // when it goes on (local time)
  cap?: number;
  today?: number;
  start?: string;
  capped?: boolean;
  tomorrow?: number;
};
