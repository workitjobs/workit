// How the window talks to Apply (the bridge contract in spec KAN-867).
// - routes: the Apply window's existing routes, through plain fetch with the window's token. In WorkIt Auto Apply's
//   window, app_window.SHIM carries each fetch to Dashboard.respond, with no port; a window
//   dashboard.py serves gets the same calls over its own address.
// - app methods: app_window.Bridge's js_api methods (queue, applied, matches, start, status, usage, settings, review_report,
//   send_report), used only when the window has them.
//   A Developer checkout's window has none, so the page shows the run as it is.
// - mock: fixtures, to design and screenshot the window with no Apply running (mock.ts).
import type { ApplyState, QueuedJob } from "./apply.ts";
import { said } from "./words.ts";

export type Upload = { name: string; data: string }; // a file's name and its bytes in base64
export type Queued = QueuedJob & { url: string }; // a job in the student's Auto Apply queue on WorkIt
export type AppliedJob = Queued & { applied_at?: string | null }; // one the student applied to, on WorkIt
// One of Find jobs' matches (app_window.Bridge.matches): a job as the queue names it, with its card's facts.
export type Match = Queued & {
  id: string;
  match: number | null;
  highlights: { text: string; detail?: string | null; met: boolean }[];
  location?: string | null;
  location_label?: string | null;
  work_style?: "onsite" | "hybrid" | "remote" | null;
  job_type?: string | null;
  experience_level?: "student" | "new_grad" | "experienced" | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_period?: string | null;
  start_term?: string | null;
  posted_at?: string | null;
};
// The Jobs page's filters Find jobs passes on, each a list of the values the website's own URL carries.
export type Filters = Partial<Record<"q" | "location" | "work_style" | "role" | "experience" | "job_type" | "posted_within", string[]>>;
export type Frame = { tile: number; number: number; jpeg: string }; // one screen of a form being filled
export type Usage = { used: number; cap: number; resets_at: string }; // model tokens today, and when the count resets

// app_window.Bridge's app methods. Each is there only when the window gives it.
export type App = Partial<{
  queue(): Promise<Queued[]>;
  applied(): Promise<AppliedJob[]>;
  matches(filters: Filters): Promise<Match[]>;
  // Each form's screen newer than the number `seen` has for its tile, as a JPEG: what a Worker's Chrome shows.
  frames(seen: Record<number, number>): Promise<Frame[]>;
  start(links: string[]): Promise<number>;
  status(): Promise<{ running: boolean; said: string }>;
  usage(): Promise<Usage>;
  settings(): Promise<void>;
  // A job's posting in the student's own browser: only a link a tile or item of this run lists. False: it opened nothing.
  open_posting(url: string): Promise<boolean>;
  // Report a problem with one Application (D26): what the report holds, a line each; then Send Report sends that
  // same report, named by the same id.
  review_report(category: string, note: string, contact_ok: boolean, application_id: string, include: boolean): Promise<{ parts: string[] }>;
  send_report(application_id: string): Promise<{ said: string }>;
}>;

export type Bridge = {
  watch(on: (state: ApplyState) => void, lost?: () => void): () => void; // lost: /state got no answer this time
  answer(id: string, question: string, answer: string | Upload): Promise<void>;
  approve(id: string, essays?: string[]): Promise<void>;
  open(worker: number): Promise<void>; // bring that form's Chrome window forward
  fillAgain(id: string): Promise<void>;
  letGo(id: string): Promise<void>; // Not applying to this one: its held form closes, unsubmitted
  submit(id: string): Promise<void>; // Approve and submit: Apply presses the held form's Submit, once
  cancelAuto(id: string): Promise<void>; // Cancel an Auto-submit countdown: the form waits for the student
  // Stop applying: the run ends, nothing submitted, and app_window.Bridge shows the queue again. `newOnly`: no job
  // waiting starts, and every filled form stays open for the student.
  stop(newOnly?: boolean): Promise<void>;
  remove(link: string): Promise<void>; // take a job that hasn't started out of the run
  app: Promise<App>; // never settles in a window with no app methods
};

declare global {
  interface Window {
    pywebview?: { api?: Record<string, (...args: unknown[]) => Promise<unknown>> };
    APPLY_TOKEN?: string; // the window's token, put in the page when it is served
    REPORT_CATEGORIES?: Record<string, string>; // what a report can be about (apply.report.CATEGORIES), put in with it
  }
}

// Apply's refusal, in the student's words (words.ts).
const failed = (raw: unknown) => new Error(typeof raw === "string" && raw ? said(raw) : "Apply didn't take that.");
const UNANSWERED = "Apply didn't take that. Is it still running?";

// The app's answer, or its {error} as a thrown Error. A method that broke (a Python exception) says only that
// Apply didn't take it: its own words are for the log, not the student.
async function called<T>(method: (...args: unknown[]) => Promise<unknown>, ...args: unknown[]): Promise<T> {
  const got = (await method(...args).catch(() => {
    throw failed("");
  })) as { error?: string } | T;
  if (got && typeof got === "object" && "error" in got) throw failed(got.error);
  return got as T;
}

export const NAMES = ["queue", "applied", "matches", "frames", "start", "status", "usage", "settings", "open_posting", "review_report", "send_report"] as const;

function appMethods(): Promise<App> {
  return new Promise((done) => {
    const found = () => {
      const api = window.pywebview?.api;
      if (!api) return;
      const app: App = {};
      for (const name of NAMES) if (typeof api[name] === "function") Object.assign(app, { [name]: (...args: unknown[]) => called(api[name], ...args) });
      if (Object.keys(app).length) done(app);
    };
    if (window.pywebview?.api) found();
    else window.addEventListener("pywebviewready", found, { once: true });
  });
}

export function routes(token: string, app: Promise<App> = appMethods()): Bridge {
  const post = async (path: string, body: unknown) => {
    const reply = await fetch(path, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", "X-Apply-Token": token },
    }).catch(() => {
      throw new Error(UNANSWERED); // no answer at all: Apply stopped, or is restarting
    });
    if (!reply.ok) throw failed(((await reply.json().catch(() => ({}))) as { error?: string }).error);
  };
  return {
    watch(on, lost) {
      let stop = false;
      const tick = async () => {
        try {
          // front=1: the student is looking, so Apply sends no notice of what the window already shows.
          const reply = await fetch(`/state${document.hasFocus() ? "?front=1" : ""}`);
          if (!reply.ok) throw new Error(`/state: ${reply.status}`);
          const state = await reply.json();
          if (!stop) on(state);
        } catch {
          if (!stop) lost?.(); // Apply stopped or restarting: the next tick tries again
        }
        if (!stop) setTimeout(tick, 1000);
      };
      tick();
      return () => void (stop = true);
    },
    answer: (id, question, answer) => post("/answer", typeof answer === "string" ? { id, question, answer } : { id, question, answer: "", file: answer }),
    approve: (id, essays) => post("/approve", essays ? { id, essays } : { id }),
    open: (worker) => post(`/show/${worker}`, {}),
    fillAgain: (id) => post("/fill-again", { id }),
    letGo: (id) => post("/let-go", { id }),
    submit: (id) => post("/submit", { id }),
    cancelAuto: (id) => post("/auto-cancel", { id }),
    stop: (newOnly) => post("/stop", newOnly ? { new_only: true } : {}),
    remove: (link) => post("/remove", { link }),
    app,
  };
}

export async function connect(): Promise<Bridge> {
  if (window.APPLY_TOKEN) return routes(window.APPLY_TOKEN);
  const { mock } = await import("./mock.ts");
  return mock(new URLSearchParams(location.search).get("scenario") ?? "needs");
}
