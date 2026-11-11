import assert from "node:assert/strict";
import { test } from "node:test";

import { dateAndTime } from "./date-time.ts";

const NOW = new Date("2026-11-10T20:00:00Z");

test("this year's instant reads as its month, day and time on the viewer's clock", () => {
  assert.equal(dateAndTime("2026-11-10T20:42:00Z", NOW, "America/New_York"), "Nov 10, 3:42 PM");
});

test("another year's instant adds the year", () => {
  assert.equal(
    dateAndTime("2025-10-23T19:42:00Z", NOW, "America/New_York"),
    "Oct 23, 2025, 3:42 PM",
  );
});

test("the day and the year are the viewer's: a UTC morning is the evening before in New York", () => {
  assert.equal(
    dateAndTime("2026-01-01T02:05:00Z", NOW, "America/New_York"),
    "Dec 31, 2025, 9:05 PM",
  );
});
