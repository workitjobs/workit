import assert from "node:assert/strict";
import { test } from "node:test";

import { placesOf } from "./format.ts";

test("a US place loses its country prefix and an HQ tag", () => {
  assert.deepEqual(placesOf("USA Wilmington, MA - HQ"), ["Wilmington, MA"]);
  assert.deepEqual(placesOf("US - Pittsburgh, PA"), ["Pittsburgh, PA"]);
  assert.deepEqual(placesOf("United States: Austin, TX (HQ)"), ["Austin, TX"]);
});

test("a remote place and a place abroad keep their words", () => {
  assert.deepEqual(placesOf("US Remote"), ["US Remote"]);
  assert.deepEqual(placesOf("Remote, US"), ["Remote, US"]);
  assert.deepEqual(placesOf("Canada - Richmond Hill, ON"), ["Canada - Richmond Hill, ON"]);
  assert.deepEqual(placesOf("USA"), ["USA"]);
});
