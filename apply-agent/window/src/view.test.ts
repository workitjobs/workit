import assert from "node:assert/strict";
import { test } from "node:test";

import type { Shown } from "./apply.ts";
import { addsJobs, answerOf, appliedJobs, bar, changes, checks, asking, chosen, classify, clip, filledIn, flagged, headline, HANDOFF, HOW_IT_WORKS, submittedLine, WAITING_FOR_SCREEN, stopActions, limit, notStarted, queueNote, shortcut, startWords, stopWords, usageLine, usedShare, view, wantedFields, ago, needsYou, runLine, working } from "./view.ts";

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
  assert.equal(v.stopped.length, 2);
});

test("a failed or skipped job didn't go through, with its reason in the student's words", () => {
  // Each label as verdict() in dashboard.py gives it, by the Application's status.
  const cases: [Partial<Shown>, string][] = [
    [{ tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: the page took too long to respond" }, "We couldn't finish filling this one."],
    [{ tone: "ended", kind: "skipped", status: "not eligible", label: "Skipped: you don't qualify (needs US work authorization)" }, "You don't qualify (needs US work authorization)"],
    [{ tone: "ended", kind: "skipped", status: "closed", label: "Skipped: no longer taking applications" }, "This job was taken down. Nothing to do."],
    [{ tone: "ended", kind: "skipped", status: "already applied", label: "Already applied" }, "You already applied. Nothing to do."],
    [{ tone: "ended", kind: "skipped", status: "skipped", label: "Skipped: you already applied to this job" }, "You already applied. Nothing to do."],
    [{ tone: "ended", kind: "skipped", status: "paused", label: "Paused at Claude's usage limit; it goes on by itself" }, "Stopped at today's limit. Try again once it resets"],
    // A job that reached WorkIt's Usage cap and ended failed, in UsageLimitHit's words (KAN-837).
    [{ tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: UsageLimitHit: Usage limit reached; resets at 2026-11-17 19:00:00" }, "Stopped at today's limit. Try again once it resets"],
  ];
  for (const [over, reason] of cases) {
    const v = view({ tiles: [], items: [job({ id: 3, ...over })] });
    assert.deepEqual(
      v.stopped.map((j) => [j.company, j.reason]),
      [["Stripe", reason]],
      String(over.status),
    );
  }
});

test("a reason in Apply's developer words is said plainly, never as it is", () => {
  const cases: [Partial<Shown>, string][] = [
    [{ tone: "failed", status: "failed", label: "Couldn't finish: setup: ask_model: workit needs a WorkIt sign-in" }, "We couldn't finish filling this one."],
    [{ tone: "failed", status: "failed", label: "Couldn't finish: the rehearsal stopped" }, "We couldn't finish filling this one."],
    [{ tone: "failed", status: "failed", label: "Couldn't finish: Claude fill gave up on the page" }, "We couldn't finish filling this one."],
    [{ tone: "ended", kind: "skipped", status: "skipped", label: "Skipped: today's limit reached; 3 more go tomorrow" }, "Today's limit was reached before it started"],
    [{ tone: "ended", kind: "skipped", status: "skipped", label: "Skipped: OpenAI takes at most 5 applications in any 180 days" }, "OpenAI takes at most 5 applications in any 180 days"],
  ];
  for (const [over, reason] of cases) assert.equal(view({ tiles: [], items: [job({ id: 3, ...over })] }).stopped[0].reason, reason, String(over.label));
});

test("Try again is offered only where Apply still holds the job's page to fill again", () => {
  const v = view({
    tiles: [
      job({ tone: "failed", posting_url: "https://held", again: true }),
      job({ tone: "ended", status: "not eligible", posting_url: "https://ruled-out", again: true }),
      job({ tone: "ended", status: "already applied", posting_url: "https://before" }), // never opened: no page held
      job({ tone: "ended", status: "paused", posting_url: "https://paused" }), // goes on by itself
    ],
    items: [job({ tone: "failed", posting_url: "https://gone", id: 7 })], // its Worker moved on: no tile
  });
  assert.deepEqual(
    v.stopped.map((j) => [j.key, j.retry]),
    [
      ["https://held", "tile-0"],
      ["https://ruled-out", "tile-1"],
      ["https://before", undefined],
      ["https://paused", undefined],
      ["https://gone", undefined],
    ],
  );
});

test("a job tried again is back among those still being worked on", () => {
  // Its item still says how it failed; its tile fills it anew.
  const v = view({ tiles: [job({ tone: "filling", posting_url: "https://held" })], items: [job({ tone: "failed", posting_url: "https://held", id: 2 })] });
  assert.deepEqual([v.stopped.length, v.working.map((j) => j.key)], [0, ["https://held"]]);
});

test("a job with no posting is told apart by company and role, or by its own id when either is missing", () => {
  const bare = (over: Partial<Shown>): Shown => ({ tone: "needs", kind: "check", posting_url: undefined, ...over });
  const v = view({
    tiles: [],
    items: [
      bare({ id: 1, company: "Acme", role: undefined }),
      bare({ id: 2, company: "Acme", role: undefined }),
      bare({ id: 3, company: "Acme", role: "SWE" }),
      bare({ id: 4, company: "Acme", role: "SWE" }),
    ],
  });
  assert.deepEqual(v.todo.map((j) => j.id), ["1", "2", "3"]);
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

test("the heading counts the questions waiting, not the jobs that ask them", () => {
  const six = job({ tone: "needs", kind: "missing fact", questions: ["a", "b", "c", "d", "e", "f"] });
  assert.equal(headline(view({ tiles: [], items: [six] })), "6 quick questions for you");
  const one = job({ tone: "needs", kind: "missing fact", posting_url: "https://o", questions: ["a"] });
  assert.equal(headline(view({ tiles: [], items: [six, one] })), "7 quick questions for you");
});

test("with only jobs that didn't go through left, the heading says so", () => {
  const failed = (url: string) => job({ tone: "failed", posting_url: url });
  assert.equal(headline(view({ tiles: [], items: [failed("https://a"), failed("https://b")] })), "2 applications didn't go through");
  assert.equal(headline(view({ tiles: [], items: [failed("https://a")] })), "1 application didn't go through");
  const sent = job({ tone: "submitted", posting_url: "https://s" });
  assert.equal(headline(view({ tiles: [], items: [failed("https://a"), sent] })), "1 application didn't go through");
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

test("the usage bar shows the share of today's limit used, never as tokens and never past full", () => {
  // Faults: the bar counting what is left, a share rounded up (100% and amber before `limit` says so), a share past
  // 100% at a cap a failed call went over, a cap of 0 as empty.
  const at = (d: Date) => d.toISOString().slice(11, 16);
  const usage = (used: number, cap = 80_000) => ({ used, cap, resets_at: "2026-11-16T05:00:00Z" });
  const shares = [0, 20_000, 52_400, 63_700, 79_700, 80_000, 86_000].map((used) => usedShare(usage(used)));
  assert.deepEqual(shares, [0, 25, 65, 79, 99, 100, 100]);
  assert.equal(usedShare(usage(0, 0)), 100);
  assert.equal(usageLine(usage(52_400), at), "65% used · resets at 05:00");
});

test("the daily limit is said in words only from 80%, never as tokens", () => {
  const at = (d: Date) => d.toISOString().slice(11, 16);
  const usage = (used: number) => ({ used, cap: 1000, resets_at: "2026-11-16T05:00:00Z" });
  assert.equal(limit(usage(799), at), "");
  assert.equal(limit(usage(800), at), "You're close to today's limit.");
  // At the cap with no run paused (none going, or a reading before the run's pause shows), when applying works again.
  assert.equal(limit(usage(1000), at), "You've reached today's limit. You can apply again from 05:00.");
  assert.equal(limit(usage(1200), at), "You've reached today's limit. You can apply again from 05:00.");
});

test("a run Apply paused at the cap says so, with or without a usage reading", () => {
  const at = (d: Date) => d.toISOString().slice(11, 16);
  const paused = { paused: true, reason: "usage cap", paused_until: "2026-11-16T05:30:00Z" };
  const words = "You've reached today's limit, so applying is paused. It starts again at 05:30.";
  assert.equal(limit(null, at, paused), words);
  assert.equal(limit({ used: 100, cap: 1000, resets_at: "2026-11-16T05:00:00Z" }, at, paused), words);
  assert.equal(limit(null, at, { paused: false }), "");
  assert.equal(limit(null, at), "");
});

const QUEUE = [
  { url: "https://stripe/1", company: "Stripe", title: "SWE Intern" },
  { url: "https://ramp/1", company: "Ramp", title: "New Grad SWE" },
];

test("Start sends the ticked jobs and the pasted link, and counts them", () => {
  assert.deepEqual(chosen(QUEUE, [true, false], " https://figma/1 "), ["https://stripe/1", "https://figma/1"]);
  assert.equal(startWords(2), "Start applying to 2 jobs");
  assert.equal(startWords(1), "Start applying to 1 job");
  assert.equal(startWords(0), "Start applying");
});

test("a pasted job already ticked in the queue counts once, and text that isn't a link not at all", () => {
  assert.deepEqual(chosen(QUEUE, [true, true], "https://ramp/1"), ["https://stripe/1", "https://ramp/1"]);
  assert.deepEqual(chosen(QUEUE, [false, false], "ramp.com"), []);
});

test("an empty queue says so and points to WorkIt and the paste box; an unread one says Bridge.queue's error", () => {
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

const press = (key: string, over: Partial<Parameters<typeof shortcut>[0]> = {}) => shortcut({ key, tag: "BODY", ...over }, 3);

test("1 to 9 pick an option, Enter saves and S skips the to-do", () => {
  assert.deepEqual(press("1"), { pick: 0 });
  assert.deepEqual(press("3"), { pick: 2 });
  assert.equal(press("4"), null); // the question has three options
  assert.equal(press("0"), null);
  assert.equal(press("Enter"), "save");
  assert.equal(press("s"), "skip");
  assert.equal(press("S"), "skip");
  assert.equal(press("x"), null);
});

test("no shortcut fires while the student types in a box, or with a modifier held", () => {
  for (const at of [{ tag: "INPUT", type: "text" }, { tag: "INPUT" }, { tag: "TEXTAREA" }, { tag: "SELECT" }, { tag: "DIV", editable: true }])
    for (const key of ["1", "Enter", "s"]) assert.equal(press(key, at), null, `${key} in ${at.tag}`);
  assert.equal(press("s", { mods: true }), null); // Cmd-S, Ctrl-1...
  assert.equal(press("1", { mods: true }), null);
});

test("a ticked box or a focused button still takes the shortcuts, but Enter there presses the button itself", () => {
  assert.deepEqual(press("2", { tag: "INPUT", type: "checkbox" }), { pick: 1 });
  assert.equal(press("s", { tag: "BUTTON" }), "skip");
  assert.equal(press("Enter", { tag: "BUTTON" }), null);
});

test("each job waiting to start is named as the queue named it, a pasted one by its site", () => {
  const v = view({
    tiles: [],
    items: [],
    run: {
      mode: "rehearsal",
      queued: 2,
      waiting: [
        { link: "https://jobs.lever.co/acme/2", company: "Acme", title: "Intern", company_domain: "acme.com" },
        { link: "https://www.careers.example.com/jobs/42" },
      ],
    },
  });
  assert.deepEqual(
    v.waiting.map((w) => [w.link, w.company, w.role]),
    [
      ["https://jobs.lever.co/acme/2", "Acme", "Intern"],
      ["https://www.careers.example.com/jobs/42", "careers.example.com", ""],
    ],
  );
  assert.equal(v.waiting[0].source.company_domain, "acme.com");
  assert.equal(v.running, true);
  assert.equal(headline(v), "We're on it");
});

test("the idle board has no run to stop and nothing waiting", () => {
  const v = view({ tiles: [], items: [], run: {} });
  assert.deepEqual([v.running, v.waiting, v.queued], [false, [], 0]);
});

test("Stop applying names the filled forms it closes, and offers Stop new ones only first while jobs wait", () => {
  // A held form (its tile's `again`) counts; one submitted, one still filling and an item's stale `again` don't.
  const v = view({
    tiles: [
      job({ tone: "ready", again: true, posting_url: "https://a" }),
      job({ tone: "needs", kind: "missing fact", again: true, posting_url: "https://b" }),
      job({ tone: "submitted", again: true, posting_url: "https://c" }),
      job({ posting_url: "https://d" }),
    ],
    items: [job({ tone: "ready", again: true, posting_url: "https://e" })],
    run: { mode: "rehearsal", queued: 0 },
  });
  assert.equal(v.held, 2);
  assert.deepEqual(stopWords(v), { ask: "Stop? 2 filled forms waiting for you will close. Nothing gets submitted.", all: "Stop" });
  assert.deepEqual(stopWords({ held: 3, queued: 2 }), { ask: "Stop starting new jobs? Your 3 filled forms stay open.", newOnly: "Stop new ones only", all: "Stop and close all 3" });
  assert.deepEqual(stopWords({ held: 1, queued: 1 }), { ask: "Stop starting new jobs? Your filled form stays open.", newOnly: "Stop new ones only", all: "Stop and close it" });
  assert.equal(stopWords({ held: 0, queued: 0 }).ask, "Stop every application? Nothing gets submitted.");
});

test("a form the student isn't applying to leaves the pile, with its earlier item", () => {
  const v = view({
    tiles: [job({ tone: "ready", again: false, let_go: true, posting_url: "https://a" }), job({ tone: "ready", again: true, posting_url: "https://b" })],
    items: [job({ tone: "ready", id: 3, posting_url: "https://a" })],
  });
  assert.deepEqual(v.todo.map((j) => j.source.posting_url), ["https://b"]);
  assert.equal(v.held, 1);
  // Its tile on to the next job: the let-go form's item stays gone.
  const after = view({ tiles: [job({ tone: "filling", posting_url: "https://c" })], items: [job({ tone: "ready", id: 3, let_go: true, posting_url: "https://a" })] });
  assert.deepEqual(after.todo, []);
  assert.deepEqual(after.working.map((j) => j.source.posting_url), ["https://c"]);
});

test("+ Add jobs shows whenever no run is going and the window can start one, never during a run", () => {
  const idle = view({ tiles: [], items: [], run: {} });
  const run = view({ tiles: [job({})], items: [], run: { mode: "rehearsal", queued: 0 } });
  assert.equal(addsJobs(idle, true), true);
  assert.equal(addsJobs(run, true), false); // app_window.Bridge.start refuses a second run
  assert.equal(addsJobs(idle, false), false); // a Developer checkout's window has no queue or Start
});

test("Applied lists this run's submitted jobs, then what WorkIt has from before, each once", () => {
  const sent = view({
    tiles: [job({ tone: "submitted", company: "Stripe", posting_url: "https://boards.greenhouse.io/stripe/1", link: "https://stripe.com/jobs/1" })],
    items: [],
  }).applied;
  const earlier = [
    { url: "https://stripe.com/jobs/1", company: "Stripe", title: "SWE Intern", applied_at: "2026-11-15T10:00:00Z" }, // this run's, already on WorkIt
    { url: "https://jobs.lever.co/acme/3", company: "Acme", title: "Intern", company_domain: "acme.com", applied_at: "2026-11-02T10:00:00Z" },
    { url: "https://jobs.lever.co/acme/3", company: "Acme", title: "Intern", applied_at: null }, // WorkIt listing it twice
  ];
  const all = appliedJobs(sent, earlier);
  assert.deepEqual(all.map((j) => [j.company, j.status]), [["Stripe", "submitted"], ["Acme", "submitted"]]);
  assert.equal(all[1].source.company_domain, "acme.com");
  assert.deepEqual(appliedJobs(sent, null).map((j) => j.company), ["Stripe"]); // WorkIt not read (yet)
});

test("the Submit card lists only what Apply says it did: checked against the profile, a resume attached", () => {
  const resume = [{ label: "Resume/CV", name: "Resume.pdf" }];
  assert.deepEqual(checks(job({ tone: "ready", asked: 22, verified: true, files: resume })), [
    "All 22 questions answered",
    "Checked against your WorkIt profile",
    "Resume attached",
  ]);
  assert.deepEqual(checks(job({ tone: "ready", files: [{ label: "Unofficial transcript", name: "t.pdf" }] })), ["Every question answered"]);
  assert.deepEqual(checks(job({ tone: "ready", files: [{ label: "Upload your résumé", name: "r.pdf" }] })), ["Every question answered", "Resume attached"]);
});

test("a form filling with no count yet shows a bar that moves, never a made-up share", () => {
  const [counted] = view({ tiles: [job({ filled: 14, asked: 22 })], items: [] }).working;
  const [uncounted] = view({ tiles: [job({})], items: [] }).working;
  const [checking] = view({ tiles: [job({ tone: "verifying" })], items: [] }).working;
  assert.equal(bar(counted), 14 / 22);
  assert.equal(bar(uncounted), "unknown");
  assert.equal(bar(checking), "unknown");
});

test("a run whose board never showed brings the queue back, saying why it didn't start", () => {
  assert.equal(notStarted({ running: true, said: "" }), ""); // still starting: keep waiting
  assert.equal(notStarted({ running: false, said: "" }), "Your applications didn't start. Press Start to try again.");
  assert.equal(
    notStarted({ running: false, said: "Google Chrome isn't installed. Install it." }),
    "Google Chrome isn't installed. Get it from google.com/chrome, then press Start again.",
  );
  assert.equal(notStarted({ running: false, said: "The run stopped: KeyError: 'x'" }), "Applying stopped because something went wrong. Press Start to try again.");
  assert.equal(notStarted(new Error("Apply didn't take that.")), "Your applications didn't start. Press Start to try again."); // status() itself failed
});

// "What we filled" on the held card. Its fault: an answer worth a glance (one WorkIt wrote, work authorization, EEO,
// school, pay, a file) buried among the name and phone, or one marked that needs no glance.
test("what we filled puts the answers worth a glance first, in their order, then the rest in the form's", () => {
  const answers: NonNullable<Shown["answers"]> = [
    { question: "First Name", answer: "Test", from: "profile", kind: "text", topic: "" },
    { question: "Resume", answer: "r.pdf", from: "profile", kind: "file", topic: "file" },
    { question: "Gender", answer: "Decline", from: "profile", kind: "select", topic: "eeo" },
    { question: "Why us?", answer: "Because.", from: "written", kind: "textarea", topic: "" },
    { question: "Sponsorship?", answer: "No", from: "profile", kind: "select", topic: "legal" },
    { question: "Heard from?", answer: "WorkIt", from: "saved", kind: "select", topic: "" },
  ];
  const { look, rest } = filledIn(job({ tone: "ready", answers }));
  assert.deepEqual(look.map((r) => [r.question, r.glance]), [
    ["Why us?", "WorkIt wrote this"],
    ["Sponsorship?", "Work authorization"],
    ["Gender", "Demographics"],
    ["Resume", "File attached"],
  ]);
  assert.deepEqual(rest.map((r) => [r.question, r.glance]), [["First Name", ""], ["Heard from?", ""]]);
  assert.deepEqual(filledIn(job({ tone: "ready" })), { look: [], rest: [] });
});

test("a long answer is cut at a word with Show more, and a short one is left whole", () => {
  assert.deepEqual(clip("Short."), { text: "Short.", cut: false });
  const cut = clip("word ".repeat(100).trim(), 50);
  assert.ok(cut.cut && cut.text.endsWith("word…") && cut.text.length <= 51, cut.text);
});

test("the review's changes say each question, from what to what, and nothing when it changed none", () => {
  const fixed = [{ question: "Graduation", was: "May 2027", now: "May 2028" }, { question: "Start", was: "", now: "June" }];
  assert.deepEqual(changes(job({ tone: "ready", fixed })), {
    heading: "We changed 2 answers after checking",
    lines: ["Graduation: May 2027 → May 2028", "Start: blank → June"],
  });
  assert.equal(changes(job({ tone: "ready", fixed: [] })), null);
});

test("each flag is said with its question and in WorkIt's words, never Apply's", () => {
  const flags = [{ field: "Pay", why: "Pre-submit review: Claude wrote $90, more than the posting's range" }, { field: "", why: "Verify: a file is empty" }];
  assert.deepEqual(flagged(job({ tone: "needs", kind: "check", flags })), ["Pay: WorkIt wrote $90, more than the posting's range", "A file is empty"]);
});

test("a handoff's fields are named once each, from the reason's Error- lines", () => {
  const why = "Workday won't leave its 'Application Questions 1 of 2' step: Error-Are you currently employed? The field Are you currently employed? is required and must have a value. Error-Do you have IP? The field Do you have IP? is required. Error-Are you currently employed? The field Are you currently employed? is required.";
  assert.deepEqual(wantedFields(why), ["Are you currently employed?", "Do you have IP?"]);
  assert.deepEqual(wantedFields("Needs your iCIMS account"), []);
  assert.deepEqual(wantedFields(undefined), []);
});

test("each handoff says how to hand back, and never that the app solves, reads or submits", () => {
  assert.match(HANDOFF["sign-in"], /Sign in yourself.*come back here/);
  assert.match(HANDOFF.code, /We don't read your email/);
  assert.match(HANDOFF.captcha, /^Finish the check/);
  assert.match(HANDOFF.fields, /press Next there/);
  for (const line of Object.values(HANDOFF)) assert.doesNotMatch(line, /we (solve|read your|submit)/i);
});

test("a raw failure is never shown, whatever the label carries", () => {
  const raw = ["PortTimeoutError: Locator.click: Timeout 30000ms exceeded.", "TimeoutError: Oracle page didn't get there in 30 s", "Workday won't leave its step"];
  for (const why of raw) {
    const [j] = view({ tiles: [], items: [job({ id: 3, tone: "failed", status: "failed", label: `Couldn't finish: ${why}` })] }).stopped;
    assert.equal(j.reason, "We couldn't finish filling this one.", why);
    assert.equal(j.stop, "failed");
  }
});

test("a closed posting, by its status or its Closed: label, has nothing to do and no retry", () => {
  for (const over of [{ status: "closed", label: "Skipped: no longer taking applications" }, { tone: "failed" as const, status: "failed", label: "Closed: the page doesn't exist, so it was skipped" }]) {
    const v = view({ tiles: [job({ tone: "ended", again: true, ...over })], items: [] });
    const [j] = v.stopped;
    assert.equal(j.reason, "This job was taken down. Nothing to do.");
    assert.deepEqual(stopActions(j, true), { finish: false, site: false });
  }
});

test("a failure offers the company's site and, while its form is held, finishing it yourself", () => {
  const held = view({ tiles: [job({ tone: "failed", status: "failed", posting_url: "https://held", again: true })], items: [] }).stopped[0];
  assert.deepEqual(stopActions(held, true), { finish: true, site: true });
  assert.deepEqual(stopActions(held, false), { finish: true, site: false }); // a window that can't open links
  const gone = view({ tiles: [], items: [job({ tone: "failed", status: "failed", posting_url: "https://gone", id: 7 })] }).stopped[0];
  assert.deepEqual(stopActions(gone, true), { finish: false, site: true });
  const applied = view({ tiles: [], items: [job({ tone: "ended", status: "already applied", id: 8 })] }).stopped[0];
  assert.deepEqual(stopActions(applied, true), { finish: false, site: false });
});

test("the done line counts this run's submitted jobs, not the student's earlier ones", () => {
  const v = view({ tiles: [job({ tone: "submitted", posting_url: "https://a" }), job({ tone: "submitted", posting_url: "https://b" })], items: [job({ tone: "submitted", from: "tracker", posting_url: "https://old", id: 9 })] });
  assert.equal(submittedLine(v), "2 applications submitted this run.");
  assert.equal(submittedLine(view({ tiles: [job({ tone: "submitted" })], items: [] })), "1 application submitted this run.");
  assert.equal(submittedLine(view({ tiles: [], items: [job({ tone: "submitted", from: "tracker", id: 9 })] })), "");
});

test("the how-it-works strip and the live wait say what happens next", () => {
  assert.match(HOW_IT_WORKS, /you press Submit\. Filled forms wait for you as long as you need\./);
  assert.match(WAITING_FOR_SCREEN, /It can take a minute the first time\./);
});

const NOW = Date.parse("2026-11-25T12:00:00");
const waiting = (over: Partial<Shown>): Shown => job({ tone: "needs", kind: "needs sign-in", ...over });

test("the Needs you list puts forms ready to submit first and says how long each waited", () => {
  const v = view({
    tiles: [
      waiting({ company: "Amazon", posting_url: "https://a", worker: 0, since: NOW / 1000 - 180 }),
      job({ tone: "ready", company: "Stripe", posting_url: "https://s2", worker: 1, since: NOW / 1000 - 720 }),
    ],
    items: [],
  });
  assert.deepEqual(
    needsYou(v.todo, NOW).map((n) => [n.company, n.words, n.at]),
    [
      ["Stripe", "Ready to submit · 12 min", 1],
      ["Amazon", "Sign in needed · 3 min", 0],
    ],
  );
});

test("a to-do with no start time says what it asks and nothing more, and an ended item's time is when it ended", () => {
  const v = view({ tiles: [], items: [fact({ at: "2026-11-25T11:50:00" }), waiting({ id: "5", posting_url: "https://x", company: "Ramp" })] });
  assert.deepEqual(needsYou(v.todo, NOW).map((n) => n.words), ["Sign in needed", "Question for you · 10 min"]);
});

test("a wait reads in minutes, then hours", () => {
  assert.equal(ago(NOW - 20_000, NOW), "just now");
  assert.equal(ago(NOW - 59 * 60_000, NOW), "59 min");
  assert.equal(ago(NOW - 125 * 60_000, NOW), "2 h 5 min");
  assert.equal(ago(NOW - 120 * 60_000, NOW), "2 h");
  assert.equal(ago(undefined, NOW), "");
});

test("the run's line counts every job of this run, and none of an earlier run's", () => {
  const v = view({
    tiles: [job({ posting_url: "https://f1" }), job({ posting_url: "https://f2" }), waiting({ posting_url: "https://w", worker: 2 })],
    items: [job({ tone: "submitted", posting_url: "https://d" }), job({ tone: "submitted", posting_url: "https://old", from: "tracker" })],
    run: { mode: "rehearsal", queued: 1 },
  });
  assert.equal(runLine(v), "1 of 5 done · 1 needs you · 2 filling · 1 waiting");
  assert.equal(runLine(view({ tiles: [], items: [] })), "");
  assert.equal(runLine(view({ tiles: [job({ tone: "failed", posting_url: "https://p" })], items: [], run: { mode: "rehearsal" } })), "0 of 1 done · 1 didn't go through");
});

test("a form being worked on says how long, and the step only when Apply's line is one the student knows", () => {
  const filling = view({ tiles: [job({ doing: "Writing answers for page 2", since: NOW / 1000 - 360 })], items: [] }).working[0];
  assert.equal(working(filling, NOW), "Filling · 6 min");
  assert.equal(filling.step, "Writing answers");
  const other = view({ tiles: [job({ doing: "Claude is rehearsing", tone: "verifying", since: NOW / 1000 - 60 })], items: [] }).working[0];
  assert.equal(working(other, NOW), "Checking · 1 min");
  assert.equal(other.step, undefined);
  assert.equal(view({ tiles: [job({ doing: "Handoff to Browser 2" })], items: [] }).working[0].step, undefined);
});
