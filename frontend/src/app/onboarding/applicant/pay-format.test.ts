import assert from "node:assert/strict";
import { test } from "node:test";

import { formatPay, payAmount } from "./pay-format.ts";

test("a yearly goal shows as dollars with commas", () => {
  assert.equal(formatPay("90000", "year"), "$90,000");
  assert.equal(formatPay("$1,250,000", "year"), "$1,250,000");
  assert.equal(formatPay("120k", "year"), "$120");
  // No cents on a year's figure: it ends at the point.
  assert.equal(formatPay("85000.50", "year"), "$85,000");
});

test("an hourly goal keeps up to two places of cents", () => {
  assert.equal(formatPay("22.5", "hour"), "$22.5");
  assert.equal(formatPay("22.509", "hour"), "$22.50");
  assert.equal(formatPay("22.", "hour"), "$22.");
  assert.equal(formatPay(".5", "hour"), "$0.5");
  assert.equal(formatPay("1.2.3", "hour"), "$1.23");
});

test("nothing typed, or only noise, is an empty field", () => {
  assert.equal(formatPay("", "year"), "");
  assert.equal(formatPay("$", "year"), "");
  assert.equal(formatPay("abc", "hour"), "");
  assert.equal(formatPay("0090", "year"), "$90");
});

test("the field's text reads back as a figure", () => {
  assert.equal(payAmount("$90,000"), 90000);
  assert.equal(payAmount("$22.50"), 22.5);
  assert.equal(payAmount("$0"), null);
  assert.equal(payAmount(""), null);
});
