import assert from "node:assert/strict";
import { test } from "node:test";

import { fillTotals, healthQuery, matchesFilters, NO_FILL_FILTERS, percent } from "./fill-health.ts";

test("the fill-health query keeps a day count from 1 to 90 and a plain engine version", () => {
  assert.equal(
    healthQuery({ days: "7", engine_version: "v0.3.2-105-gfcaaf20" }),
    "?days=7&engine_version=v0.3.2-105-gfcaaf20",
  );
  assert.equal(healthQuery({}), "?days=14");
  assert.equal(healthQuery({ days: "400", engine_version: "a b&c" }), "?days=14");
  assert.equal(healthQuery({ days: ["1", "2"] }), "?days=1");
});

test("a share reads as a whole percent", () => {
  assert.equal(percent(2 / 3), "67%");
  assert.equal(percent(0), "0%");
  assert.equal(percent(1), "100%");
});

const row = (job_system: string, fills: number, needs_you_rate: number, errors: string[] = []) => ({
  day: "2026-11-20",
  job_system,
  fills,
  clean_share: 1,
  needs_you_rate,
  top_errors: errors.map((name) => ({ name, count: 1 })),
});

test("fill totals add the fills, and list each job system's fills, most first", () => {
  const rows = [row("lever", 2, 0), row("greenhouse", 5, 0), row("lever", 4, 0)];
  assert.deepEqual(fillTotals(rows), {
    fills: 11,
    systems: [
      { job_system: "lever", fills: 6 },
      { job_system: "greenhouse", fills: 5 },
    ],
  });
  assert.deepEqual(fillTotals([]), { fills: 0, systems: [] });
});

test("a fill row is filtered by job system, by its needs-you rate and by its errors", () => {
  const clean = row("lever", 3, 0.05);
  const broken = row("workday", 3, 0.4, ["no_option", "timeout"]);
  assert.ok(matchesFilters(clean, NO_FILL_FILTERS) && matchesFilters(broken, NO_FILL_FILTERS));
  assert.ok(!matchesFilters(clean, { ...NO_FILL_FILTERS, system: "workday" }));
  assert.ok(matchesFilters(broken, { ...NO_FILL_FILTERS, needsYou: "0.25" }));
  assert.ok(!matchesFilters(clean, { ...NO_FILL_FILTERS, needsYou: "0.25" }));
  assert.ok(!matchesFilters(broken, { ...NO_FILL_FILTERS, needsYou: "0.5" }));
  assert.ok(matchesFilters(broken, { ...NO_FILL_FILTERS, errors: "with" }));
  assert.ok(!matchesFilters(clean, { ...NO_FILL_FILTERS, errors: "with" }));
  assert.ok(matchesFilters(clean, { ...NO_FILL_FILTERS, errors: "none" }));
  assert.ok(matchesFilters(broken, { ...NO_FILL_FILTERS, errors: "name:timeout" }));
  assert.ok(!matchesFilters(broken, { ...NO_FILL_FILTERS, errors: "name:crash" }));
});
