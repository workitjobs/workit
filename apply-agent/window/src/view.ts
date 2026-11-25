// Apply's state, as the student sees it: a pile of things to do, one at a
// time, and the jobs WorkIt is still working on. A job is in one or the other.
import type { ApplyState, Filled, Run, Shown, Waiting } from "./apply.ts";
import type { AppliedJob, Queued, Usage } from "./bridge.ts";
import { DEVELOPER, said } from "./words.ts";

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
  stop?: Stop; // what kind of end it was, which says the next step
  retry?: string; // what /fill-again names it by, when Apply holds its page to fill again: Try again
  held?: boolean; // its form is open and waiting for the student: Stop applying or quitting closes it
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
  held: number; // forms open and waiting for the student, which a full Stop closes
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

// How a job that didn't go through ended, which decides what the student can do next: a closed posting and one
// already applied to have nothing to do; a failure can be tried again, or done on the company's own site; the rest
// (not eligible, an employer's limit, today's usage limit) say their own reason.
export type Stop = "closed" | "applied" | "failed" | "limit" | "other";

export const CLOSED = "This job was taken down. Nothing to do.";
export const APPLIED = "You already applied. Nothing to do.";
export const COULDNT = "We couldn't finish filling this one.";

export function stopOf(shown: Shown): Stop {
  const label = (shown.label ?? "").replace(/^Skipped: /, "");
  // A job that reached the Usage cap mid-form ends there; the run waits for the reset before the next one
  // (rehearsal._after_the_limit). "Usage limit reached" since KAN-837 (adapters.UsageLimitHit); "hit" before.
  if (shown.status === "paused" || /usage limit (hit|reached)/i.test(label) || /^today's limit reached/.test(label)) return "limit";
  if (shown.status === "closed" || /^closed\b|no longer taking applications|taken down|page doesn't exist/i.test(label)) return "closed";
  if (shown.status === "already applied" || /\balready applied\b/i.test(label)) return "applied";
  if (shown.tone === "failed" || shown.status === "failed") return "failed";
  return "other";
}

// Why a job didn't go through, from verdict()'s label: "Skipped: " said by the list's own heading, and no
// developer words (words.ts): a cause in Apply's own words is said plainly instead. A failure never shows its cause
// (a timeout, a raw exception): it says it couldn't finish, and the row offers what to do.
export const reason = (shown: Shown) => {
  const label = (shown.label ?? "").replace(/^Skipped: /, "");
  const stop = stopOf(shown);
  if (stop === "closed") return CLOSED;
  if (stop === "applied") return APPLIED;
  if (/^today's limit reached/.test(label)) return "Today's limit was reached before it started";
  if (stop === "limit") return "Stopped at today's limit. Try again once it resets";
  if (stop === "failed") return COULDNT;
  if (DEVELOPER.test(label)) return COULDNT;
  return label ? label[0].toUpperCase() + label.slice(1) : "Something went wrong";
};

// What a stopped row offers besides Try again. `finish`: its form is still held, so the student can open it and finish
// it. `site`: the job's own posting in their browser, for a failure when the window can open it. A closed or applied
// job offers nothing: there is nothing to do.
export const stopActions = (job: Job, canOpenSite: boolean) => ({
  finish: job.stop === "failed" && !!job.held && job.worker !== undefined,
  site: job.stop === "failed" && canOpenSite && !!job.source.posting_url,
});

// One job, one key: its posting, else its company and role when it has both, else its own id.
const keyOf = (s: Shown) => String(s.posting_url || (s.company && s.role ? `${s.company}|${s.role}` : s.id));

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
    if (tile?.let_go) continue; // not applying to it: its card goes
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
      stop: c.status === "stopped" ? stopOf(shown) : undefined,
      retry: c.status === "stopped" && tile && (tile.again || tile.askable || tile.refill) ? `tile-${tile.worker}` : undefined,
      held: !!tile?.again && c.status !== "submitted",
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
    held: jobs.filter((j) => j.held).length,
  };
}

// The Applied page: this run's submitted jobs, then what the student applied to on WorkIt before (Bridge.applied),
// each once. A job is the same by its link or its form's address, or by its company and role.
export function appliedJobs(thisRun: Job[], earlier: AppliedJob[] | null): Job[] {
  const seen = new Set(thisRun.flatMap((j) => [j.source.link, j.source.posting_url, `${j.company}|${j.role}`]).filter(Boolean));
  const jobs = [...thisRun];
  for (const a of earlier ?? []) {
    const company = a.company || site(a.url);
    const role = a.title ?? "";
    if (seen.has(a.url) || (role && seen.has(`${company}|${role}`))) continue;
    seen.add(a.url).add(`${company}|${role}`);
    const source: Shown = { tone: "submitted", company, role, posting_url: a.url, logo_url: a.logo_url ?? undefined, company_domain: a.company_domain ?? undefined };
    jobs.push({ key: a.url, company, role, status: "submitted", source });
  }
  return jobs;
}

// What the Submit card says WorkIt checked: only what Apply says it did. A resume went in when a file the form was
// given answers its resume question.
export function checks(s: Shown): string[] {
  return [
    s.asked ? `All ${s.asked} questions answered` : "Every question answered",
    s.verified && "Checked against your WorkIt profile",
    s.files?.some((f) => /r[eé]sum[eé]|\bcv\b/i.test(f.label ?? "")) && "Resume attached",
  ].filter((line): line is string => !!line);
}

// Where an answer came from, in the student's words.
export const FROM: Record<Filled["from"], string> = { profile: "Your profile", saved: "Your saved answer", written: "Written by WorkIt" };

// Why an answer is worth a glance before Submit, most first: what WorkIt wrote, then work authorization and
// sponsorship, demographics, school and graduation, pay, and the files attached. A wrong one of these is what an
// employer reads first; the rest (a name, a phone number) comes straight from the student's profile.
const GLANCE: [(a: Filled) => boolean, string][] = [
  [(a) => a.from === "written", "WorkIt wrote this"],
  [(a) => a.topic === "legal", "Work authorization"],
  [(a) => a.topic === "eeo", "Demographics"],
  [(a) => a.topic === "school", "Education"],
  [(a) => a.topic === "pay", "Pay"],
  [(a) => a.topic === "file" || a.kind === "file", "File attached"],
];

export type Row = Filled & { glance: string }; // glance: why to look at it, or "" for one that needs no glance

// "What we filled": the answers worth a glance first (`look`, in GLANCE's order, then the form's), then the rest in
// the form's order. Only what Apply sent in the state: nothing the window reads or guesses itself.
export function filledIn(s: Shown): { look: Row[]; rest: Row[] } {
  const rows = (s.answers ?? []).map((a) => {
    const at = GLANCE.findIndex(([test]) => test(a));
    return { ...a, glance: at < 0 ? "" : GLANCE[at][1], at };
  });
  const look = rows.filter((r) => r.at >= 0).sort((a, b) => a.at - b.at);
  const strip = ({ at: _, ...row }: Row & { at: number }): Row => row;
  return { look: look.map(strip), rest: rows.filter((r) => r.at < 0).map(strip) };
}

// A long answer (an essay) cut at a word to `max` characters, with whether it was cut: "Show more" shows the rest.
export function clip(text: string, max = 220): { text: string; cut: boolean } {
  if (text.length <= max) return { text, cut: false };
  const at = text.lastIndexOf(" ", max);
  return { text: `${text.slice(0, at > max / 2 ? at : max).trimEnd()}…`, cut: true };
}

// What the Pre-submit review changed after checking, as the card says it: a heading and a line each.
export function changes(s: Shown): { heading: string; lines: string[] } | null {
  const fixed = s.fixed ?? [];
  if (!fixed.length) return null;
  return {
    heading: `We changed ${plural(fixed.length, "answer")} after checking`,
    lines: fixed.map((f) => `${f.question}: ${f.was || "blank"} → ${f.now}`),
  };
}

// Each answer verifying says needs the student, in plain words: its question, then why. Apply's own names for itself
// and its checks (words.ts' DEVELOPER) are said as WorkIt's.
export function flagged(s: Shown): string[] {
  return (s.flags ?? []).map((f) => {
    const why = f.why
      .replace(/^(Verify|Pre-submit (review|check failed\.?)):?\s*/i, "")
      .replace(/\bClaude\b/g, "WorkIt");
    return f.field ? `${f.field}: ${why}` : why.charAt(0).toUpperCase() + why.slice(1);
  });
}

// What to do about a flagged answer: the app never submits, so the student fixes it on the form and submits there.
export const FIX_IN_FORM = "Fix it in the form, then press Submit there.";

// What each handoff card says to do, in the student's voice: how to hand the form back, since the app never presses Submit,
// types into an employer's sign-in, solves a captcha or reads email.
export const WAITING_IN_CHROME = "Waiting for you in Chrome…";

export const HANDOFF = {
  "sign-in": "Sign in yourself in the window that opens, then come back here. We'll carry on.",
  code: "Check your email for the code and type it into the form. We don't read your email.",
  captcha: "Finish the check in the window that opens.",
  finish: "We got as far as we could. The rest of the form needs you.",
  fields: "Fill these in the form, then press Next there.",
} as const;

// The fields an ATS (Workday) won't go past a step without, from the Worker's reason ("... Error-<field> The field <field>
// is required ..."), each once and in the form's order. None when the reason names none.
export function wantedFields(why: string | undefined): string[] {
  const found = [...(why ?? "").matchAll(/Error-(.+?)\s+The field\b/g)].map((m) => m[1].trim());
  return [...new Set(found)];
}

// How far a job still being worked on has got, for its bar: the share of questions filled, or "unknown" while Apply
// hasn't counted them (it counts them when a fill pauses or ends) or checks the answers. Never a made-up share.
export const bar = (job: Job): number | "unknown" => (job.progress === undefined ? "unknown" : job.progress);

// + Add jobs (the queue screen again): whenever no run is going, in a window that can start one. Never during a run,
// since app_window.Bridge.start refuses a second while one goes.
export const addsJobs = (v: View, canStart: boolean) => canStart && !v.running;

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

// Stop applying's question, and its buttons. With jobs still waiting to start, Stop new ones only comes first: it
// keeps every filled form open. A full Stop names the filled forms it closes, so none is lost unawares.
export function stopWords(v: Pick<View, "held" | "queued">): { ask: string; newOnly?: string; all: string } {
  const forms = plural(v.held, "filled form");
  if (v.queued > 0)
    return {
      ask: !v.held ? "Stop starting new jobs? Nothing gets submitted." : v.held === 1 ? "Stop starting new jobs? Your filled form stays open." : `Stop starting new jobs? Your ${forms} stay open.`,
      newOnly: "Stop new ones only",
      all: v.held ? `Stop and close ${v.held === 1 ? "it" : `all ${v.held}`}` : "Stop everything",
    };
  return { ask: v.held ? `Stop? ${forms} waiting for you will close. Nothing gets submitted.` : "Stop every application? Nothing gets submitted.", all: "Stop" };
}

// The page's heading: what the student should do now, in a few words. Questions count one by one, since a job
// asks each on its own card.
export function headline(v: View): string {
  const n = v.todo.length;
  if (!n && (v.working.length || v.queued)) return "We're on it";
  if (!n) return v.stopped.length ? `${plural(v.stopped.length, "application")} didn't go through` : "You're all caught up";
  if (v.todo.every((j) => j.ask === "question")) {
    const asked = v.todo.reduce((sum, j) => sum + Math.max(1, j.source.questions?.length ?? 0), 0);
    return `${plural(asked, "quick question")} for you`;
  }
  if (v.todo.every((j) => j.ask === "submit")) return `${plural(n, "application")} ready to submit`;
  return `${plural(n, "thing")} for you to do`;
}

const clock = (d: Date) => d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

const pausedAt = (resets: Date, at: (resets: Date) => string) => `You've reached today's limit, so applying is paused. It starts again at ${at(resets)}.`;

// The share of today's Usage cap used, 0 to 100, for the usage bar (Usage): never a token count, which means nothing
// to a student. Rounded down, so it says 100% and turns amber at 80% only once `limit` says so too: rounded, 79,700
// of 80,000 read "100% used" while forms still filled. A cap of 0 is a cap reached.
export const usedShare = (usage: Usage) => (usage.cap > 0 ? Math.min(100, Math.floor((usage.used / usage.cap) * 100)) : 100);

// The bar's own line: how much of today's limit is used, and when it starts again from nothing.
export const usageLine = (usage: Usage, at: (resets: Date) => string = clock) =>
  `${usedShare(usage)}% used · resets at ${at(new Date(usage.resets_at))}`;

// Today's model use against the Usage cap, in words beside the bar: nothing under 80%. A run paused at the cap says so,
// and when it goes on, from /state (the run waits for the reset: rehearsal._after_the_limit); a reading at the cap
// with no run paused says when applying works again.
export function limit(usage: Usage | null, at: (resets: Date) => string = clock, run?: Run): string {
  if (run?.paused && run.paused_until) return pausedAt(new Date(run.paused_until), at);
  if (!usage) return "";
  if (usage.used >= usage.cap) return `You've reached today's limit. You can apply again from ${at(new Date(usage.resets_at))}.`;
  return usage.used >= usage.cap * 0.8 ? "You're close to today's limit." : "";
}

// What Start runs: the queue's ticked jobs, then the pasted link if it is one and isn't ticked already.
export function chosen(queue: Queued[], ticked: boolean[], pasted: string): string[] {
  const links = queue.filter((_, i) => ticked[i]).map((q) => q.url);
  const link = pasted.trim();
  return /^https?:\/\/\S+$/.test(link) && !links.includes(link) ? [...links, link] : links;
}

export const startWords = (n: number) => (n ? `Start applying to ${plural(n, "job")}` : "Start applying");

// How long "Starting N applications…" waits for the run's board before it asks Apply whether the run is going.
export const STARTING_WAIT = 30_000;

// Why a run whose board never showed didn't start, from app_window.Bridge.status() (or its failure): "" while it
// is still going, so the page keeps waiting; else the line under Start, with the queue back.
export function notStarted(status: { running: boolean; said: string } | Error): string {
  if (status instanceof Error) return "Your applications didn't start. Press Start to try again.";
  if (status.running) return "";
  return status.said ? said(status.said) : "Your applications didn't start. Press Start to try again.";
}

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
