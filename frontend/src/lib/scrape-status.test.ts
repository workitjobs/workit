import assert from "node:assert/strict";
import { test } from "node:test";

import {
  datesOf,
  dayLabel,
  moved,
  rangeOf,
  resized,
  statusOf,
  systemName,
  windowHref,
  windowOf,
} from "./scrape-status.ts";

const NOW = Date.parse("2026-11-19T12:00:00Z");
const system = (last_read_at: string | null) => ({
  ats: "ashby",
  boards: 100,
  read: 1,
  last_read_at,
});
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
  assert.deepEqual(windowOf({}), { days: 14, back: 0 });
  assert.deepEqual(windowOf({ days: "30", back: "500" }), { days: 30, back: 60 });
  assert.deepEqual(windowOf({ days: "13", back: "-4" }), { days: 14, back: 0 });
  // An address from before the arrows moved by the period still opens: its `step` is ignored.
  const older = { days: "7", back: "7", step: "month" };
  assert.deepEqual(windowOf(older), { days: 7, back: 7 });
});

test("a window moves one whole period at a time and stops at both ends", () => {
  const newest = windowOf({ days: "14" });
  assert.equal(moved(newest, 1), null);
  assert.deepEqual(moved(newest, -1), { days: 14, back: 14 });
  assert.deepEqual(moved({ days: 14, back: 14 }, 1), newest);
  // The longest period is the whole history, so it cannot move.
  assert.equal(moved(windowOf({ days: "90" }), -1), null);
  assert.equal(moved(windowOf({ days: "90" }), 1), null);
});

test("the last step back is cut to the days the history still has", () => {
  // 90 days hold six periods of 14 days and 6 days more.
  assert.deepEqual(moved({ days: 14, back: 70 }, -1), { days: 14, back: 76 });
  assert.equal(moved({ days: 14, back: 76 }, -1), null);
  // The step forward from there lands on a whole number of periods again.
  assert.deepEqual(moved({ days: 14, back: 76 }, 1), { days: 14, back: 70 });
  // So does a step forward from any other distance an address names.
  assert.deepEqual(moved({ days: 14, back: 7 }, 1), { days: 14, back: 0 });
});

test("a new period keeps the window's last day where the history allows", () => {
  assert.deepEqual(resized({ days: 14, back: 28 }, 30), { days: 30, back: 28 });
  // 90 days are the whole history, so they can only end today.
  assert.deepEqual(resized({ days: 14, back: 28 }, 90), { days: 90, back: 0 });
  assert.deepEqual(resized({ days: 7, back: 83 }, 30), { days: 30, back: 60 });
});

test("a window's address leaves out a zero distance back", () => {
  assert.equal(windowHref({ days: 14, back: 14 }), "/admin/scrape-health?days=14&back=14");
  assert.equal(windowHref({ days: 30, back: 0 }), "/admin/scrape-health?days=30");
  assert.equal(
    windowHref({ days: 7, back: 7 }, "/admin/fill-health", { engine_version: "v1", none: "" }),
    "/admin/fill-health?days=7&back=7&engine_version=v1",
  );
});

test("a window's days end on today less its distance back", () => {
  const dates = datesOf({ days: 7, back: 7 }, "2026-11-19");
  assert.equal(dates.length, 7);
  assert.equal(dates[0], "2026-11-06");
  assert.equal(dates[6], "2026-11-12");
});

test("a day and a range read in words, in UTC", () => {
  assert.equal(dayLabel("2026-08-25"), "Aug 25");
  assert.equal(rangeOf(["2026-11-09", "2026-11-10", "2026-11-22"]), "Nov 9 to Nov 22");
});

test("a hiring system's id reads as its name", () => {
  assert.equal(systemName("icims"), "iCIMS");
  assert.equal(systemName("workday"), "Workday");
});
