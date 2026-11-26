import assert from "node:assert/strict";
import { test } from "node:test";

import { groupRepeats } from "./notification-groups.ts";

const item = (id: string, kind: string) => ({ id, kind });
const ids = (groups: { id: string }[][]) => groups.map((group) => group.map(({ id }) => id));

test("a run of one kind is one group, newest first", () => {
  const items = [item("a", "job_alert"), item("b", "job_alert"), item("c", "job_alert")];
  assert.deepEqual(ids(groupRepeats(items)), [["a", "b", "c"]]);
});

test("another kind between two runs keeps them apart, in time order", () => {
  const items = [
    item("a", "job_alert"),
    item("b", "reply"),
    item("c", "job_alert"),
    item("d", "job_alert"),
  ];
  assert.deepEqual(ids(groupRepeats(items)), [["a"], ["b"], ["c", "d"]]);
});

test("no items, no groups", () => {
  assert.deepEqual(groupRepeats([]), []);
});
