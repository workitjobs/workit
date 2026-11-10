import assert from "node:assert/strict";
import test from "node:test";

import type { PreviewEntry } from "@/lib/resume-actions";

import { draftOfPreview, previewOfDraft, rowOfPreview } from "./preview-entry.ts";

const CLUB: PreviewEntry = {
  section: "leadership",
  title: "Treasurer",
  organization: "Lakeview Robotics Club",
  location: null,
  start_month: "2025-09",
  end_month: null,
  end_kind: "present",
  degree: null,
  field_of_study: null,
  gpa: null,
  gpa_scale: null,
  coursework: [],
  honors: null,
  link: null,
  issuer: null,
  award_date: null,
  custom_section_id: null,
  section_name: null,
  bullets: ["Managed a $4,000 annual budget for 30 members"],
  replaces: ["older-club-row"],
};

test("the shared row gets each bullet with its place as its id", () => {
  assert.deepEqual(rowOfPreview(CLUB).bullets, [
    { id: "0", text: "Managed a $4,000 annual budget for 30 members" },
  ]);
});

test("the editor's draft holds the fields and a box per bullet, never the replaced rows", () => {
  const draft = draftOfPreview(CLUB);
  assert.deepEqual(draft.bullets, [{ text: "Managed a $4,000 annual budget for 30 members" }]);
  assert.equal("replaces" in draft, false);
  assert.equal(draft.organization, "Lakeview Robotics Club");
});

test("an edit that keeps the title and organization keeps what the entry replaces", () => {
  const draft = draftOfPreview(CLUB);
  const edited = previewOfDraft(
    {
      ...draft,
      title: "  treasurer ",
      bullets: [...draft.bullets, { text: "Ran the spring fundraiser" }],
    },
    CLUB,
  );
  assert.deepEqual(edited.replaces, ["older-club-row"]);
  assert.deepEqual(edited.bullets, [
    "Managed a $4,000 annual budget for 30 members",
    "Ran the spring fundraiser",
  ]);
});

test("a new title stops naming the replaced rows, and an empty bullet box goes", () => {
  const edited = previewOfDraft(
    { ...draftOfPreview(CLUB), title: "Vice President", bullets: [{ text: "  " }] },
    CLUB,
  );
  assert.deepEqual(edited.replaces, []);
  assert.deepEqual(edited.bullets, []);
});
