import assert from "node:assert/strict";
import { test } from "node:test";

import { answerText, ordered, parseAnswer, sameQuestion } from "./answer-bank.ts";

test("a list answer survives its box: joined, split again, none of these stays none", () => {
  assert.equal(answerText(["Finance", "Software"]), "Finance; Software");
  assert.deepEqual(parseAnswer(" Finance ;Software; ", true), ["Finance", "Software"]);
  assert.deepEqual(parseAnswer("", true), []);
  assert.equal(parseAnswer("  A friend; at work  ", false), "A friend; at work");
});

test("drafts waiting for review come first, each set in question order", () => {
  const rows = ordered([
    { question: "B?", answer: "x", own: true },
    { question: "Z?", answer: "x", own: false },
    { question: "A?", answer: "x", own: true },
    { question: "C?", answer: "x", own: false },
  ]);
  assert.deepEqual(
    rows.map((r) => r.question),
    ["C?", "Z?", "A?", "B?"],
  );
});

test("a question matches one the bank holds whatever its case, spacing, quotes or asterisk", () => {
  assert.ok(sameQuestion("Do you have a driver’s  license? *", "do you have a driver's license?"));
  assert.ok(!sameQuestion("Do you have a license?", "Do you have a driver's license?"));
});
