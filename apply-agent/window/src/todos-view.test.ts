import assert from "node:assert/strict";
import { test } from "node:test";

import type { Todo } from "./bridge.ts";
import { dueWords, lists, scanLine } from "./todos-view.ts";

const NOW = new Date(2026, 10, 27, 15, 0).getTime(); // Nov 27, 2026, local time

test("a due date reads from today, and soon is urgent", () => {
  const said = ["2026-11-25", "2026-11-26", "2026-11-27", "2026-11-28", "2026-11-30", "2026-12-05", null].map((d) => dueWords(d, NOW));
  assert.deepEqual(
    said.map((s) => s.text),
    ["Overdue by 2 days", "Overdue by 1 day", "Due today", "Due tomorrow", "Due in 3 days", "Due Dec 5", "No due date"],
  );
  assert.deepEqual(
    said.map((s) => s.urgent),
    [true, true, true, true, false, false, false],
  );
});

test("done and dismissed to-dos leave the open list", () => {
  const todo = (id: string, status: Todo["status"]) => ({ id, status }) as Todo;
  const { open, closed } = lists([todo("a", "open"), todo("b", "done"), todo("c", "dismissed"), todo("d", "open")]);
  assert.deepEqual(open.map((t) => t.id), ["a", "d"]);
  assert.deepEqual(closed.map((t) => t.id), ["b", "c"]);
});

test("the last scan says what it read, found or why it failed", () => {
  assert.equal(scanLine(null, true), "Scanning your mail…");
  assert.equal(scanLine(null, false), "Not scanned yet.");
  assert.equal(scanLine({ read: 1, added: 0, updated: 0, by_model: 0, model: "", errors: ["No app password."] }, false), "Last scan failed: No app password.");
  assert.equal(scanLine({ read: 12, added: 2, updated: 0, by_model: 0, model: "no model: read by rules", errors: [] }, false), "Scanned 12 mails: 2 new. (no model: read by rules)");
});
