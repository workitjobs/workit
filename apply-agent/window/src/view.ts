// Apply's state, as the student sees it: a pile of things to do, one at a
// time, and the jobs WorkIt is still working on. A job is in one or the other.
import type { ApplyState, Shown, Waiting } from "./apply.ts";
import type { Queued, Usage } from "./bridge.ts";

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
  id?: string; // what /answer and /approve name it by: its item's id
  worker?: number; // what /show/<k> names its form's Chrome window by: its tile's place on the board
  reason?: string; // why it didn't go through, in the student's words
  retry?: string; // what /fill-again names it by, when Apply holds its page to fill again: Try again
  source: Shown; // the tile over its item, so a tile's to-do keeps the item's questions
};

export type View = {
  todo: Job[]; // what waits on the student, most blocking first
  working: Job[]; // filling or checking: nothing to do
  applied: Job[];
  stopped: Job[]; // failed or skipped: "Didn't go through"
  queued: number; // waiting to start
  waiting: Waits[]; // those of them Apply names: Remove takes one out
  running: boolean; // a run's board, which Stop applying ends; not the idle board
};

// A job waiting to start, as a row shows it. `link` is what /remove names it by.
export type Waits = { link: string; company: string; role: string; source: Waiting };

// A pasted link has no WorkIt job to name it: its site does.
const site = (link: string) => {
  try {
    return new URL(link).hostname.replace(/^www\./, "");
  } catch {
    return link;
  }
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

// Why a job didn't go through, from verdict()'s label: "Skipped: " said by the list's own heading, and no
// developer words.
export const reason = (shown: Shown) => {
  const said = (shown.label ?? "").replace(/^Skipped: /, "").replace("Claude's usage limit", "today's limit");
  return said ? said[0].toUpperCase() + said.slice(1) : "Something went wrong";
};

const keyOf = (s: Shown) => String(s.posting_url || `${s.company}|${s.role}` || s.id);

export function view(state: ApplyState): View {
  // A tile is the form as it is now; an item is how an earlier pass ended, or a live form's questions. The tile
  // says where the job is; the item keeps what the student answers it through.
  const tiles = new Map<string, Shown>();
  const items = new Map<string, Shown>();
  state.tiles.forEach((tile, k) => {
    if (tile.tone !== "idle" && !tiles.has(keyOf(tile))) tiles.set(keyOf(tile), { ...tile, worker: k });
  });
  for (const item of state.items) if (!items.has(keyOf(item))) items.set(keyOf(item), item);
  const jobs: Job[] = [];
  for (const key of new Set([...tiles.keys(), ...items.keys()])) {
    const tile = tiles.get(key);
    const item = items.get(key);
    const shown = tile ? { ...item, ...tile } : item!;
    if (!tile && item!.tone === "idle") continue;
    const c = classify(shown);
    if (item?.answered && (!tile || c.status === "todo")) continue; // answered in the window: it waits on the student no more
    jobs.push({
      key,
      company: shown.company || "A job",
      role: shown.role || "",
      ...c,
      progress: c.status === "filling" && shown.asked ? (shown.filled ?? 0) / shown.asked : undefined,
      id: item?.id === undefined ? undefined : String(item.id),
      worker: tile ? tile.worker : item?.worker,
      reason: c.status === "stopped" ? reason(shown) : undefined,
      retry: c.status === "stopped" && tile && (tile.again || tile.askable || tile.refill) ? `tile-${tile.worker}` : undefined,
      source: { ...shown, questions: item?.questions ?? tile?.questions },
    });
  }
  return {
    todo: jobs.filter((j) => j.ask).sort((a, b) => ORDER.indexOf(a.ask!) - ORDER.indexOf(b.ask!)),
    working: jobs.filter((j) => j.status === "filling" || j.status === "checking"),
    applied: jobs.filter((j) => j.status === "submitted"),
    stopped: jobs.filter((j) => j.status === "stopped"),
    queued: state.run?.queued ?? 0,
    waiting: (state.run?.waiting ?? []).map((w) => ({ link: w.link, company: w.company || site(w.link), role: w.title || "", source: w })),
    running: !!state.run?.mode,
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

const clock = (d: Date) => d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

// Today's model use against the Usage cap, in words: nothing under 80%, and never a token count.
export function limit(usage: Usage, at: (resets: Date) => string = clock): string {
  if (usage.used >= usage.cap) return `You've reached today's limit, so applying is paused. It starts again at ${at(new Date(usage.resets_at))}.`;
  return usage.used >= usage.cap * 0.8 ? "You're close to today's limit." : "";
}

// What Start runs: the queue's ticked jobs, then the pasted link if it is one and isn't ticked already.
export function chosen(queue: Queued[], ticked: boolean[], pasted: string): string[] {
  const links = queue.filter((_, i) => ticked[i]).map((q) => q.url);
  const link = pasted.trim();
  return /^https?:\/\/\S+$/.test(link) && !links.includes(link) ? [...links, link] : links;
}

export const startWords = (n: number) => `Start applying to ${plural(n, "job")}`;

// The line over the paste box: why there is no queue to tick. Nothing while it is read, or once it lists jobs.
export function queueNote(queue: Queued[] | Error | null): string {
  if (queue instanceof Error) return queue.message;
  return queue?.length === 0 ? "Your Auto Apply queue on WorkIt is empty. Add jobs to it on WorkIt, or paste a job's link below." : "";
}

// How a question is answered on the card: buttons for a few options, a list beyond, boxes to tick for
// pick-all-that-apply, a file picker, or a box to type in.
export type Form = "buttons" | "list" | "checks" | "file" | "text";

export type Asked = { question: string; form: Form; options: string[]; optional: boolean; planned: string };

// The job's next question, skipping those the student answered already (`done`), which Apply drops a moment later.
export function asking(source: Shown, done: string[]): Asked | undefined {
  const question = source.questions?.find((q) => !done.includes(q));
  if (question === undefined) return undefined;
  const choice = source.choices?.[question];
  const options = choice?.kind === "file" ? [] : (choice?.options ?? []);
  const form: Form =
    choice?.kind === "file" ? "file" : !options.length ? "text" : choice?.kind === "multi_select" ? "checks" : options.length > 4 ? "list" : "buttons";
  return { question, form, options, optional: source.required?.[question] === false, planned: source.planned?.[question] ?? "" };
}

// What /answer gets for the options picked: several joined by "; " in the form's order, as the Answer cell holds them.
export const answerOf = (asked: Asked, picks: string[]) => asked.options.filter((o) => picks.includes(o)).join("; ");

// The to-do card's keys: 1 to 9 pick an option, Enter saves, S skips the to-do. None while the student types in a
// box, or with Cmd, Ctrl or Alt held (the window's own shortcuts). Enter on a focused button is that button's.
export type Key = { pick: number } | "save" | "skip" | null;

const TICKS = ["checkbox", "radio", "button", "submit", "file"];

export function shortcut(e: { key: string; tag: string; type?: string; editable?: boolean; mods?: boolean }, options: number): Key {
  const typing = e.editable || e.tag === "TEXTAREA" || e.tag === "SELECT" || (e.tag === "INPUT" && !TICKS.includes(e.type ?? "text"));
  if (typing || e.mods) return null;
  if (/^[1-9]$/.test(e.key)) return Number(e.key) <= options ? { pick: Number(e.key) - 1 } : null;
  if (e.key === "Enter") return e.tag === "BUTTON" ? null : "save";
  return e.key.toLowerCase() === "s" ? "skip" : null;
}
