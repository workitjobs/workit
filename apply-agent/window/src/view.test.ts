import assert from "node:assert/strict";
import { test } from "node:test";

import type { Shown } from "./apply.ts";
import { answerOf, asking, chosen, classify, headline, limit, queueNote, startWords, view } from "./view.ts";

const job = (over: Partial<Shown>): Shown => ({ tone: "filling", company: "Stripe", role: "SWE Intern", posting_url: "https://s", ...over });

test("each tone verdict() gives lands where the student expects it", () => {
  const cases: [Shown["tone"], ReturnType<typeof classify>][] = [
    ["filling", { status: "filling" }],
    ["verifying", { status: "checking" }],
    ["ready", { status: "todo", ask: "submit" }],
    ["submitted", { status: "submitted" }],
    ["failed", { status: "stopped" }],
    ["ended", { status: "stopped" }],
  ];
  for (const [tone, seen] of cases) assert.deepEqual(classify(job({ tone })), seen, tone);
});

test("each kind of to-do verdict() gives gets its own card", () => {
  const cases: [string, string][] = [
    ["needs sign-in", "sign-in"],
    ["missing fact", "question"],
    ["needs code", "code"],
    ["captcha", "captcha"],
    ["check", "check"],
    ["held", "approve"],
    ["blocked", "finish"],
    ["handoff", "finish"],
  ];
  for (const [kind, ask] of cases) assert.deepEqual(classify(job({ tone: "needs", kind })), { status: "todo", ask }, kind);
});

test("a form with its code filled is one to submit", () => {
  assert.deepEqual(classify(job({ tone: "ready", kind: "code filled" })), { status: "todo", ask: "submit" });
});

test("a job shows once: its tile over its earlier item", () => {
  const v = view({ tiles: [job({ filled: 5, asked: 10 })], items: [job({ tone: "needs", kind: "missing fact" })] });
  assert.equal(v.todo.length, 0);
  assert.equal(v.working.length, 1);
  assert.equal(v.working[0].progress, 0.5);
});

test("stopped jobs are in neither the pile nor the working list", () => {
  const v = view({ tiles: [job({ tone: "failed" })], items: [job({ tone: "ended", posting_url: "https://e" })] });
  assert.equal(v.todo.length + v.working.length + v.applied.length, 0);
});

test("idle tiles and answered items are left out", () => {
  const v = view({ tiles: [job({ tone: "idle" })], items: [job({ tone: "needs", kind: "held", posting_url: "https://f", answered: true })] });
  assert.equal(v.todo.length + v.working.length, 0);
});

test("a sign-in comes first and a form to submit last", () => {
  const kinds = ["handoff", "held", "check", "captcha", "needs code", "missing fact", "needs sign-in"];
  const v = view({
    tiles: [],
    items: [job({ tone: "ready", posting_url: "r" }), ...kinds.map((kind) => job({ tone: "needs", kind, posting_url: kind }))],
  });
  assert.deepEqual(
    v.todo.map((j) => j.ask),
    ["sign-in", "question", "code", "captcha", "check", "approve", "finish", "submit"],
  );
  assert.equal(headline(v), "8 things for you to do");
});

test("the heading names the one kind of to-do there is, or that there is none", () => {
  const q = view({ tiles: [], items: [job({ tone: "needs", kind: "missing fact" })] });
  assert.equal(headline(q), "1 quick question for you");
  const s = view({ tiles: [], items: [job({ tone: "ready", posting_url: "a" }), job({ tone: "ready", posting_url: "b" })] });
  assert.equal(headline(s), "2 applications ready to submit");
  assert.equal(headline(view({ tiles: [job({})], items: [] })), "We're on it");
  assert.equal(headline(view({ tiles: [], items: [], run: { queued: 2 } })), "We're on it");
  assert.equal(headline(view({ tiles: [], items: [] })), "You're all caught up");
});

test("a tile's to-do is answered through its item and opened through its tile", () => {
  // A form still filling asks its Missing fact at once: the tile says so, and its live item carries the question.
  const tile = job({ tone: "needs", kind: "missing fact" });
  const live = job({ tone: "needs", kind: "missing fact", id: "live-1", worker: 1, questions: ["When can you start?"] });
  const [todo] = view({ tiles: [job({ tone: "idle", posting_url: "" }), tile], items: [live] }).todo;
  assert.equal(todo.id, "live-1");
  assert.equal(todo.worker, 1);
  assert.deepEqual(todo.source.questions, ["When can you start?"]);
});

test("a tile with no item is opened through its own place on the board", () => {
  const [todo] = view({ tiles: [job({ tone: "idle", posting_url: "" }), job({ tone: "ready" })], items: [] }).todo;
  assert.equal(todo.worker, 1);
});

test("a question answered in the window leaves the pile while its form fills it in", () => {
  const tile = job({ tone: "needs", kind: "missing fact" });
  const live = job({ tone: "needs", kind: "missing fact", id: "live-0", questions: ["When can you start?"], answered: true });
  assert.equal(view({ tiles: [tile], items: [live] }).todo.length, 0);
});

test("the daily limit is said in words only from 80%, never as tokens", () => {
  const at = (d: Date) => d.toISOString().slice(11, 16);
  const usage = (used: number) => ({ used, cap: 1000, resets_at: "2026-11-16T05:00:00Z" });
  assert.equal(limit(usage(799), at), "");
  assert.equal(limit(usage(800), at), "You're close to today's limit.");
  assert.equal(limit(usage(1000), at), "You've reached today's limit, so applying is paused. It starts again at 05:00.");
  assert.equal(limit(usage(1200), at), "You've reached today's limit, so applying is paused. It starts again at 05:00.");
});

const QUEUE = [
  { url: "https://stripe/1", company: "Stripe", title: "SWE Intern" },
  { url: "https://ramp/1", company: "Ramp", title: "New Grad SWE" },
];

test("Start sends the ticked jobs and the pasted link, and counts them", () => {
  assert.deepEqual(chosen(QUEUE, [true, false], " https://figma/1 "), ["https://stripe/1", "https://figma/1"]);
  assert.equal(startWords(2), "Start applying to 2 jobs");
  assert.equal(startWords(1), "Start applying to 1 job");
});

test("a pasted job already ticked in the queue counts once, and text that isn't a link not at all", () => {
  assert.deepEqual(chosen(QUEUE, [true, true], "https://ramp/1"), ["https://stripe/1", "https://ramp/1"]);
  assert.deepEqual(chosen(QUEUE, [false, false], "ramp.com"), []);
});

test("an empty queue says so and points to WorkIt and the paste box; an unread one says #613's error", () => {
  assert.equal(queueNote([]), "Your Auto Apply queue on WorkIt is empty. Add jobs to it on WorkIt, or paste a job's link below.");
  assert.equal(queueNote(new Error("WorkIt Auto Apply couldn't read your queue (offline). Paste a link instead.")), "WorkIt Auto Apply couldn't read your queue (offline). Paste a link instead.");
  assert.equal(queueNote(QUEUE), "");
  assert.equal(queueNote(null), ""); // still reading it
});

const fact = (over: Partial<Shown>): Shown => job({ tone: "needs", kind: "missing fact", id: "4", ...over });

test("a question with no options is a box, pre-filled with the answer the form refused", () => {
  const source = fact({ questions: ["When can you start?"], planned: { "When can you start?": "June 2027" } });
  assert.deepEqual(asking(source, []), { question: "When can you start?", form: "text", options: [], optional: false, planned: "June 2027" });
});

test("each kind of choice gets its own form: up to four buttons, a list beyond, boxes to tick, a file picker", () => {
  const four = ["Yes", "No", "Maybe", "Later"];
  const six = ["LinkedIn", "Handshake", "A friend", "Career fair", "WorkIt", "Other"];
  const cases: [Shown["choices"], string, string[]][] = [
    [{ q: { kind: "single", options: four } }, "buttons", four],
    [{ q: { options: ["Yes", "No"] } }, "buttons", ["Yes", "No"]],
    [{ q: { kind: "single", options: six } }, "list", six],
    [{ q: { kind: "multi_select", options: ["NYC", "SF"] } }, "checks", ["NYC", "SF"]],
    [{ q: { kind: "file", options: [] } }, "file", []],
    [{ q: { kind: "single", options: [] } }, "text", []],
  ];
  for (const [choices, form, options] of cases) {
    const asked = asking(fact({ questions: ["q"], choices }), []);
    assert.deepEqual([asked?.form, asked?.options], [form, options], form);
  }
});

test("a question is optional only when the form says so", () => {
  const source = fact({ questions: ["a", "b", "c"], required: { a: false, b: true } });
  assert.deepEqual(["a", "b", "c"].map((q) => asking(source, ["a", "b", "c"].filter((o) => o !== q))?.optional), [true, false, false]);
});

test("once a question is answered the job's next one is asked, and none once all are", () => {
  const source = fact({ questions: ["Authorized?", "Start date?"] });
  assert.equal(asking(source, ["Authorized?"])?.question, "Start date?");
  assert.equal(asking(source, ["Authorized?", "Start date?"]), undefined);
});

test("ticked boxes are sent as one answer, in the form's order, as today's window sends them", () => {
  const asked = asking(fact({ questions: ["q"], choices: { q: { kind: "multi_select", options: ["NYC", "SF", "Remote"] } } }), [])!;
  assert.equal(answerOf(asked, ["Remote", "NYC"]), "NYC; Remote");
  assert.equal(answerOf(asked, []), "");
});
