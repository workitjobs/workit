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
  flags?: { field: string; why: string }[];
  verified?: boolean;
  filled?: number;
  asked?: number;
  status?: string;
};

export type ApplyState = {
  tiles: Shown[];
  items: Shown[];
  run?: { queued?: number; cap?: number; today?: number; start?: string; capped?: boolean; tomorrow?: number };
  context?: Record<string, unknown>;
};
