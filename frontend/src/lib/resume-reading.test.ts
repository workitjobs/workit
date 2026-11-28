import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dollars,
  faults,
  type ReadingHealth,
  readingTotals,
  reasonOf,
  type RecentReading,
  routeName,
  scoredOn,
  share,
  statusOf,
} from "./resume-reading.ts";

const reading = (over: Partial<RecentReading> = {}): RecentReading => ({
  at: "2026-11-27T19:42:00Z",
  account: "3f2a81c4-0000-4000-8000-000000000000",
  route: "upload",
  read_by: "model",
  model: "gemini-3.5-flash-lite",
  reason: null,
  seconds: 3.8,
  entries: 9,
  skills: 21,
  tokens: 2630,
  ...over,
});
const failed = (reason = "model_unavailable") =>
  reading({ read_by: "parser", model: null, reason, tokens: null });

const health = (over: Partial<ReadingHealth> = {}): ReadingHealth => ({
  read_at: "2026-11-27T20:00:00Z",
  today: { used: 51, cap: 100 },
  days: [{ day: "2026-11-27", ai: 90, parser: 10 }],
  reasons: [{ reason: "no_uses_left", readings: 10, last_at: "2026-11-27T19:40:00Z" }],
  median_seconds: 3.9,
  models: [],
  accuracy: null,
  recent: [reading()],
  ...over,
});

test("a reason and a route have a name, and an unknown one shows as its key", () => {
  assert.deepEqual(reasonOf("timeout"), { label: "Model Too Slow", fault: true });
  // The daily limit and an empty file are by design, not a model's failure.
  assert.equal(reasonOf("no_uses_left").fault, false);
  assert.equal(reasonOf("no_text").fault, false);
  assert.deepEqual(reasonOf("brand_new"), { label: "brand_new", fault: false });
  assert.equal(routeName("import_again"), "Import Again");
  assert.equal(routeName("brand_new"), "brand_new");
});

test("a share is a whole percent, and a dash with no whole", () => {
  assert.equal(share(463, 559), "83%");
  assert.equal(share(0, 0), "–");
});

test("a cost under a cent keeps four places", () => {
  assert.equal(dollars(0.37), "$0.37");
  assert.equal(dollars(0.0042), "$0.0042");
  assert.equal(dollars(0), "$0.00");
});

test("the totals sum the days, and the faults only the model failures", () => {
  assert.deepEqual(
    readingTotals([
      { day: "2026-11-26", ai: 3, parser: 2 },
      { day: "2026-11-27", ai: 4, parser: 1 },
    ]),
    { ai: 7, parser: 3, all: 10 },
  );
  const at = "2026-11-27T00:00:00Z";
  assert.equal(
    faults([
      { reason: "no_uses_left", readings: 41, last_at: at },
      { reason: "model_unavailable", readings: 33, last_at: at },
      { reason: "timeout", readings: 9, last_at: at },
      { reason: "no_text", readings: 7, last_at: at },
    ]),
    42,
  );
});

test("the status is green while models answer and the limit is not reached", () => {
  assert.equal(statusOf(health()).level, "green");
});

test("a period with no reading has nothing to judge", () => {
  assert.equal(statusOf(health({ days: [], reasons: [], recent: [] })).level, "none");
});

test("the status is amber at today's limit", () => {
  const status = statusOf(health({ today: { used: 100, cap: 100 } }));
  assert.equal(status.level, "amber");
  assert.match(status.reason, /limit is reached/);
});

test("the status is amber when a model fails on more than a tenth of the readings that asked one", () => {
  const at = "2026-11-27T00:00:00Z";
  // 90 read and 10 failed is a tenth: not more, so still green.
  const tenth = { reason: "timeout", readings: 10, last_at: at };
  assert.equal(statusOf(health({ reasons: [tenth] })).level, "green");
  const more = statusOf(health({ reasons: [{ ...tenth, readings: 11 }] }));
  assert.equal(more.level, "amber");
  assert.match(more.reason, /11%/);
  // The daily limit sends many to the rule-based parser, and none of them is a failure.
  const limit = { reason: "no_uses_left", readings: 500, last_at: at };
  assert.equal(statusOf(health({ reasons: [limit] })).level, "green");
});

test("the status is red when the last five readings that asked a model all failed", () => {
  const five = [failed(), failed("timeout"), failed(), failed("wrong_shape"), failed()];
  assert.equal(statusOf(health({ recent: five })).level, "red");
  // Readings that asked no model (the limit, an empty file) are passed over.
  const between = [failed(), failed("no_uses_left"), failed(), failed("no_text"), ...five.slice(2)];
  assert.equal(statusOf(health({ recent: between })).level, "red");
  // One reply among the five, or fewer than five that asked, is not red.
  assert.notEqual(statusOf(health({ recent: [...five.slice(1), reading()] })).level, "red");
  assert.notEqual(statusOf(health({ recent: five.slice(1) })).level, "red");
});

test("a scoring run says what it was scored on", () => {
  const run = {
    ran: "2026-11-17",
    set: "made_up",
    resumes: 19,
    model: "gemini-3.5-flash-lite",
    parser: 71.5,
    ai: 93.0,
    combined: 96.8,
  };
  assert.equal(scoredOn(run), "19 made-up resumes");
  assert.equal(scoredOn({ ...run, set: "real", resumes: 1 }), "1 real resume");
});
