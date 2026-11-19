import assert from "node:assert/strict";
import { test } from "node:test";

import { datesOf, moved, statusOf, systemName, windowHref, windowOf } from "./scrape-status.ts";

const NOW = Date.parse("2026-11-19T12:00:00Z");
const system = (last_read_at: string | null) => ({ ats: "ashby", boards: 100, read: 1, last_read_at });
const boards = (failing: number) => ({
  boards: 100,
  failing,
  resting: 0,
  stale: 0,
  open_jobs: 0,
  pending: 0,
  claimed: 0,
  oldest_pending_at: null,
});

test("the status is red when no board was read in 24 hours", () => {
  const never = statusOf({ boards: boards(0), systems: [system(null)] }, NOW);
  assert.equal(never.level, "red");
  const old = statusOf({ boards: boards(0), systems: [system("2026-11-15T02:46:00Z")] }, NOW);
  assert.equal(old.level, "red");
  assert.match(old.reason, /4 days ago/);
});

test("the status is amber when more than 5% of boards are failing, else green", () => {
  const fresh = [system("2026-11-19T10:00:00Z")];
  assert.equal(statusOf({ boards: boards(6), systems: fresh }, NOW).level, "amber");
  assert.equal(statusOf({ boards: boards(5), systems: fresh }, NOW).level, "green");
});

test("a window keeps a listed period and stays inside the last 90 days", () => {
  assert.deepEqual(windowOf({}), { days: 14, back: 0, step: "week" });
  assert.deepEqual(windowOf({ days: "30", back: "500" }), { days: 30, back: 60, step: "month" });
  assert.deepEqual(windowOf({ days: "13", back: "-4", step: "month" }), {
    days: 14,
    back: 0,
    step: "month",
  });
});

test("a window moves by its step and stops at both ends", () => {
  const start = windowOf({ days: "14" });
  assert.equal(moved(start, 1), null);
  assert.deepEqual(moved(start, -1), { days: 14, back: 7, step: "week" });
  assert.equal(moved(windowOf({ days: "90" }), -1), null);
  assert.equal(windowHref({ days: 14, back: 7, step: "week" }), "/admin/scrape-health?days=14&back=7");
  assert.equal(
    windowHref({ days: 14, back: 0, step: "month" }),
    "/admin/scrape-health?days=14&step=month",
  );
});

test("a window's days end on today less its distance back", () => {
  const dates = datesOf({ days: 7, back: 7, step: "week" }, "2026-11-19");
  assert.equal(dates[0], "2026-11-06");
  assert.equal(dates[6], "2026-11-12");
});

test("a hiring system's id reads as its name", () => {
  assert.equal(systemName("icims"), "iCIMS");
  assert.equal(systemName("workday"), "Workday");
});
