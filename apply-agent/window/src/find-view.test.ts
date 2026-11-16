import assert from "node:assert/strict";
import { test } from "node:test";

import { ago, filterLabel, level, MENUS, pay } from "./find-view.ts";

test("a filter's button names the one pick, or how many", () => {
  const role = MENUS.find((m) => m.name === "role")!;
  assert.equal(filterLabel(role, []), "Role");
  assert.equal(filterLabel(role, ["software_engineer"]), "Software Engineer");
  assert.equal(filterLabel(role, ["software_engineer", "data_engineer"]), "Role · 2");
});

test("the match ring says what the website's does", () => {
  assert.deepEqual(
    [90, 85, 84, 70, 69, null].map((m) => level(m).label),
    ["Excellent Match", "Excellent Match", "Good Match", "Good Match", "Fair Match", "Fair Match"],
  );
});

test("pay reads as a person writes it", () => {
  assert.equal(pay({ salary_min: 40, salary_max: 50, salary_period: "hour" }), "$40–$50/hr");
  assert.equal(pay({ salary_min: 45, salary_max: 45, salary_period: "hour" }), "$45/hr");
  assert.equal(pay({ salary_min: 150000, salary_max: 180000, salary_period: "year" }), "$150k–$180k/yr");
  assert.equal(pay({ salary_min: null, salary_max: null, salary_period: null }), "");
});

test("a posting's age is days, then months", () => {
  const now = Date.parse("2026-11-16T12:00:00Z");
  assert.equal(ago("2026-11-16T01:00:00Z", now), "Today");
  assert.equal(ago("2026-11-15T01:00:00Z", now), "Yesterday");
  assert.equal(ago("2026-11-02T12:00:00Z", now), "14 days ago");
  assert.equal(ago("2026-09-01T12:00:00Z", now), "2 months ago");
});
