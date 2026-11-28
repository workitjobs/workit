import assert from "node:assert/strict";
import { test } from "node:test";

import { topOnSwitch } from "./scroll.ts";

// Fault: a switch that keeps the last page's scroll (no scroll to the top), or a scroll on a render of the same page,
// which would jump the student back up as the page's data updates.
test("a switch to another page scrolls to the top, and a render of the same page doesn't", () => {
  const calls: [number, number][] = [];
  const shown = topOnSwitch({ scrollTo: (x, y) => void calls.push([x, y]) });
  shown("find");
  shown("find");
  assert.deepEqual(calls, []);
  shown("todos");
  assert.deepEqual(calls, [[0, 0]]);
  shown("todos");
  shown("applied");
  shown("find");
  assert.deepEqual(calls, [[0, 0], [0, 0], [0, 0]]);
});
