import assert from "node:assert/strict";
import { test } from "node:test";

import { mergeChoices } from "./model.ts";
import { CHAPTERS, SAMPLE_BANK, sampleChoices, sampleTicked } from "./walkthrough-model.ts";

test("the path runs down the page, header first", () => {
  assert.deepEqual(
    CHAPTERS.map((c) => c.id),
    [
      "contact",
      "education",
      "experience",
      "projects",
      "skills",
      "reuse",
      "page",
      "format",
      "download",
    ],
  );
});

test("the practice examples tick on screen and start with none on", () => {
  const start = sampleChoices();
  assert.equal(sampleTicked(start), 0);
  const job = SAMPLE_BANK.entries[0];
  const ticked = mergeChoices(start, { entries: [{ entry_id: job.id, shown: true }] });
  assert.equal(sampleTicked(ticked), 1);
  // Every example is named as one, so it never passes for real data
  assert.ok(SAMPLE_BANK.entries.every((e) => /Example/.test(`${e.title} ${e.organization}`)));
});
