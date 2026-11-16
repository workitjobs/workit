// How the window talks to Apply (the bridge contract in spec KAN-867).
// - routes: the Apply window's existing routes, through plain fetch with the window's token. In WorkIt Auto Apply's
//   window, #613's shim (app_window.SHIM) carries each fetch to Dashboard.respond, with no port; a window
//   dashboard.py serves gets the same calls over its own address.
// - app methods: #613's js_api methods (queue, start, status, usage, settings), used only when the window has them.
//   A Developer checkout's window has none, so the page shows the run as it is.
// - mock: fixtures, to design and screenshot the window with no Apply running (mock.ts).
import type { ApplyState, QueuedJob } from "./apply.ts";

export type Upload = { name: string; data: string }; // a file's name and its bytes in base64
export type Queued = QueuedJob & { url: string }; // a job in the student's Auto Apply queue on WorkIt
export type Usage = { used: number; cap: number; resets_at: string }; // model tokens today, and when the count resets

// #613's app methods. Each is there only when the window gives it.
export type App = Partial<{
  queue(): Promise<Queued[]>;
  start(links: string[]): Promise<number>;
  status(): Promise<{ running: boolean; said: string }>;
  usage(): Promise<Usage>;
  settings(): Promise<void>;
}>;

export type Bridge = {
  watch(on: (state: ApplyState) => void, lost?: () => void): () => void; // lost: /state got no answer this time
  answer(id: string, question: string, answer: string | Upload): Promise<void>;
  approve(id: string, essays?: string[]): Promise<void>;
  open(worker: number): Promise<void>; // bring that form's Chrome window forward
  fillAgain(id: string): Promise<void>;
  stop(): Promise<void>; // Stop applying: the run ends, nothing submitted, and #613 shows the queue again
  remove(link: string): Promise<void>; // take a job that hasn't started out of the run
  app: Promise<App>; // never settles in a window with no app methods
};

declare global {
  interface Window {
    pywebview?: { api?: Record<string, (...args: unknown[]) => Promise<unknown>> };
    APPLY_TOKEN?: string; // the window's token, put in the page when it is served
  }
}

const failed = (said: unknown) => new Error(typeof said === "string" && said ? said : "Apply didn't take that.");
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

export const NAMES = ["queue", "start", "status", "usage", "settings"] as const;

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
    stop: () => post("/stop", {}),
    remove: (link) => post("/remove", { link }),
    app,
  };
}

export async function connect(): Promise<Bridge> {
  if (window.APPLY_TOKEN) return routes(window.APPLY_TOKEN);
  const { mock } = await import("./mock.ts");
  return mock(new URLSearchParams(location.search).get("scenario") ?? "needs");
}
