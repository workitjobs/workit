// How the window talks to Apply. One interface, three ways to reach it:
// - pywebview: the native window (design doc W5 step 2): `js_api` methods,
//   and Apply's state pushed into `window.pywebview.state`.
// - http: today's dashboard routes, for a window that dashboard.py serves.
// - mock: fixtures, to design and screenshot the window with no Apply running.
import type { ApplyState } from "./apply.ts";

export type Bridge = {
  watch(on: (state: ApplyState) => void): () => void;
  answer(id: string, question: string, answer: string): Promise<void>;
  approve(id: string, essays?: string[]): Promise<void>;
  open(worker: number): Promise<void>; // bring that form's Chrome window forward
  add(link: string): Promise<void>;
  start(): Promise<void>;
};

declare global {
  interface Window {
    pywebview?: {
      api: Record<string, (...args: unknown[]) => Promise<unknown>>;
      state: { apply?: ApplyState; addEventListener(type: "change", on: (e: { detail: { key: string; value: unknown } }) => void): void };
    };
    APPLY_TOKEN?: string;
  }
}

function pywebview(): Bridge {
  const api = () => window.pywebview!.api;
  return {
    watch(on) {
      const send = () => window.pywebview?.state.apply && on(window.pywebview.state.apply);
      const ready = () => {
        send();
        window.pywebview!.state.addEventListener("change", (e) => e.detail.key === "apply" && send());
      };
      if (window.pywebview) ready();
      else window.addEventListener("pywebviewready", ready, { once: true });
      return () => {};
    },
    answer: async (id, question, answer) => void (await api().answer(id, question, answer)),
    approve: async (id, essays) => void (await api().approve(id, essays ?? null)),
    open: async (worker) => void (await api().show(worker)),
    add: async (link) => void (await api().add(link)),
    start: async () => void (await api().start()),
  };
}

function http(token: string): Bridge {
  const post = async (path: string, body: unknown) => {
    const reply = await fetch(path, {
      method: "POST",
      body: typeof body === "string" ? body : JSON.stringify(body),
      headers: { "Content-Type": "application/json", "X-Apply-Token": token },
    });
    if (!reply.ok) throw new Error(((await reply.json().catch(() => ({}))) as { error?: string }).error || "Apply didn't take that.");
  };
  return {
    watch(on) {
      let stop = false;
      const tick = async () => {
        try {
          on(await (await fetch("/state")).json());
        } catch {
          // Apply restarting: the next tick tries again.
        }
        if (!stop) setTimeout(tick, 1000);
      };
      tick();
      return () => void (stop = true);
    },
    answer: (id, question, answer) => post("/answer", { id, question, answer }),
    approve: (id, essays) => post("/approve", essays ? { id, essays } : { id }),
    open: (worker) => post(`/show/${worker}`, {}),
    add: async () => {
      throw new Error("Add a job from the website's Auto Apply queue for now.");
    },
    start: () => post("/start", token),
  };
}

export async function connect(): Promise<Bridge> {
  if (window.pywebview || navigator.userAgent.includes("pywebview")) return pywebview();
  if (window.APPLY_TOKEN) return http(window.APPLY_TOKEN);
  const { mock } = await import("./mock.ts");
  return mock(new URLSearchParams(location.search).get("scenario") ?? "needs");
}
