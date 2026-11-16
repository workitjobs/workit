import assert from "node:assert/strict";
import { test } from "node:test";

import type { Shown } from "./apply.ts";
import { classify, headline, view } from "./view.ts";

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
