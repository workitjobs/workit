// Apply's state, as the student sees it: a pile of things to do, one at a
// time, and the jobs WorkIt is still working on. A job is in one or the other.
import type { ApplyState, Shown } from "./apply.ts";

export type Status = "filling" | "checking" | "todo" | "submitted" | "stopped";

// What a to-do asks of the student. Each kind gets its own card. Submitting is one too.
export type Ask = "sign-in" | "question" | "code" | "captcha" | "check" | "approve" | "submit" | "finish";

export type Job = {
  key: string;
  company: string;
  role: string;
  status: Status;
  ask?: Ask;
  progress?: number; // 0..1 while filling
  source: Shown;
};

export type View = {
  todo: Job[]; // what waits on the student, most blocking first
  working: Job[]; // filling or checking: nothing to do
  applied: Job[];
  queued: number;
  today: number;
  cap: number;
};

const ASKS: Record<string, Ask> = {
  "needs sign-in": "sign-in",
  "missing fact": "question",
  "needs code": "code",
  captcha: "captcha",
  check: "check",
  held: "approve",
  blocked: "finish",
  handoff: "finish",
};

// A sign-in blocks every job on its site, so it comes first; a form to submit is done, so it comes last.
const ORDER: Ask[] = ["sign-in", "question", "code", "captcha", "check", "approve", "finish", "submit"];

export function classify(shown: Shown): { status: Status; ask?: Ask } {
  switch (shown.tone) {
    case "filling":
      return { status: "filling" };
    case "verifying":
      return { status: "checking" };
    case "ready":
      return { status: "todo", ask: "submit" };
    case "submitted":
      return { status: "submitted" };
    case "needs":
      return { status: "todo", ask: ASKS[shown.kind ?? ""] ?? "finish" };
    default:
      return { status: "stopped" };
  }
}

const keyOf = (s: Shown) => String(s.posting_url || `${s.company}|${s.role}` || s.id);

export function view(state: ApplyState): View {
  const byKey = new Map<string, Job>();
  // A tile is the form as it is now; an item is how an earlier pass ended. The tile wins.
  for (const shown of [...state.tiles, ...state.items]) {
    if (shown.tone === "idle" || shown.answered) continue;
    const key = keyOf(shown);
    if (byKey.has(key)) continue;
    const c = classify(shown);
    byKey.set(key, {
      key,
      company: shown.company || "A job",
      role: shown.role || "",
      ...c,
      progress: c.status === "filling" && shown.asked ? (shown.filled ?? 0) / shown.asked : undefined,
      source: shown,
    });
  }
  const jobs = [...byKey.values()];
  const applied = jobs.filter((j) => j.status === "submitted");
  return {
    todo: jobs.filter((j) => j.ask).sort((a, b) => ORDER.indexOf(a.ask!) - ORDER.indexOf(b.ask!)),
    working: jobs.filter((j) => j.status === "filling" || j.status === "checking"),
    applied,
    queued: state.run?.queued ?? 0,
    today: state.run?.today ?? applied.length,
    cap: state.run?.cap ?? 25,
  };
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

// The page's heading: what the student should do now, in a few words.
export function headline(v: View): string {
  const n = v.todo.length;
  if (!n) return v.working.length || v.queued ? "We're on it" : "You're all caught up";
  if (v.todo.every((j) => j.ask === "question")) return `${plural(n, "quick question")} for you`;
  if (v.todo.every((j) => j.ask === "submit")) return `${plural(n, "application")} ready to submit`;
  return `${plural(n, "thing")} for you to do`;
}
