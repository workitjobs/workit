import assert from "node:assert/strict";
import { test } from "node:test";

import { DEGREES, suggestDegrees } from "./degrees.ts";

test("a short form finds its degree first", () => {
  assert.equal(suggestDegrees("BS")[0], "Bachelor of Science");
  assert.equal(suggestDegrees("B.S.")[0], "Bachelor of Science");
  assert.equal(suggestDegrees("mba")[0], "Master of Business Administration");
  assert.equal(suggestDegrees("PhD")[0], "Doctor of Philosophy");
});

test("a name's start or its words find it", () => {
  assert.equal(suggestDegrees("bachelor of a")[0], "Bachelor of Arts");
  assert.ok(suggestDegrees("master").every((name) => name.startsWith("Master")));
  assert.ok(suggestDegrees("science").includes("Master of Science"));
});

test("an empty field lists every degree, and nothing unknown is invented", () => {
  assert.equal(suggestDegrees("").length, DEGREES.length);
  assert.deepEqual(suggestDegrees("zzz"), []);
});
