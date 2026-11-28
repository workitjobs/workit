import assert from "node:assert/strict";
import { test } from "node:test";

import {
  datesOf,
  dayLabel,
  rangeOf,
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

test("a window keeps a listed period, else 14 days", () => {
  assert.deepEqual(windowOf({}), { days: 14 });
  assert.deepEqual(windowOf({ days: "30" }), { days: 30 });
  assert.deepEqual(windowOf({ days: "13" }), { days: 14 });
  // An address from before the arrows went still opens: its `back` and `step` are ignored.
  const older = { days: "7", back: "7", step: "month" };
  assert.deepEqual(windowOf(older), { days: 7 });
});

test("a window's address holds its period and the page's filters that are set", () => {
  assert.equal(windowHref({ days: 30 }), "/admin/scrape-health?days=30");
  assert.equal(
    windowHref({ days: 7 }, "/admin/fill-health", { engine_version: "v1", none: "" }),
    "/admin/fill-health?days=7&engine_version=v1",
  );
});

test("a window's days end today", () => {
  const dates = datesOf({ days: 7 }, "2026-11-19");
  assert.equal(dates.length, 7);
  assert.equal(dates[0], "2026-11-13");
  assert.equal(dates[6], "2026-11-19");
});

test("a day and a range read in words, in UTC", () => {
  assert.equal(dayLabel("2026-08-25"), "Aug 25");
  assert.equal(rangeOf(["2026-11-09", "2026-11-10", "2026-11-22"]), "Nov 9 to Nov 22");
});

test("a hiring system's id reads as its name", () => {
  assert.equal(systemName("icims"), "iCIMS");
  assert.equal(systemName("workday"), "Workday");
});
