import assert from "node:assert/strict";
import { test } from "node:test";

import { factLabel, parseValue, valueText } from "./app-answers.ts";

// Fault: an edit saved a list or a number as text, which the Fill engine then reads as a different answer.
test("an edit keeps its value's kind", () => {
  assert.deepEqual(parseValue(" Python \n\nGo", ["Rust"]), ["Python", "Go"]);
  assert.equal(parseValue("40", 30), 40);
  assert.equal(parseValue("forty", 30), null);
  assert.equal(parseValue("  he/him ", "they/them"), "he/him");
});

test("a value and a key read as words", () => {
  assert.equal(valueText(true), "Yes");
  assert.equal(valueText(""), "Skipped");
  assert.equal(factLabel("screeners.willing_to_travel"), "Willing to travel");
});
