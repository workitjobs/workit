import assert from "node:assert/strict";
import { test } from "node:test";

import { answerText, parseAnswer, rows, sameQuestion, words } from "./bank.ts";

test("the bank's rows come drafts first, a reviewed one as the student's, and none of these as none", () => {
  const got = rows({
    bank_note: "",
    bank: [
      { question: "B?", answer: "x", reviewed: true },
      { question: "Skill areas", answer: [], reviewed: false },
      { question: "A?", answer: "x", reviewed: false },
    ],
  });
  assert.deepEqual(got.map((r) => [r.question, r.own, r.none]), [["A?", false, false], ["Skill areas", false, true], ["B?", true, false]]);
});

test("a list answer survives its box, and a question matches whatever its case, spacing, quotes or asterisk", () => {
  assert.equal(answerText(["Finance", "Software"]), "Finance; Software");
  assert.deepEqual(parseAnswer(" Finance ;Software; ", true), ["Finance", "Software"]);
  assert.deepEqual(parseAnswer("", true), []);
  assert.ok(sameQuestion("Do you have a driver’s  license? *", "do you have a driver's license?"));
});

test("a profile key reads as words", () => {
  assert.equal(words("identity.legal_first_name"), "Legal first name");
  assert.equal(words("voluntary_self_id"), "Voluntary self id");
});
