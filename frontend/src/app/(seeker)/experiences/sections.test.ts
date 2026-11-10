import assert from "node:assert/strict";
import { test } from "node:test";

import type { BankEntry } from "@/lib/bank-actions";

import { changesOf, draftOf, emptyDraft, isFixed, rowGaps } from "./sections.ts";

// The fields the entry PATCH declares (backend/app/schemas/bank.py,
// EntryUpdate). It forbids any other key: one more and the whole edit is a
// 422, "Extra inputs are not permitted" (KAN-505).
const PATCH_FIELDS = [
  "title",
  "organization",
  "location",
  "start_month",
  "end_month",
  "end_kind",
  "degree",
  "field_of_study",
  "gpa",
  "gpa_scale",
  "coursework",
  "honors",
  "link",
  "issuer",
  "award_date",
];

// An entry as GET /bank sends it: its fields, plus the id, bullets,
// `resume_ids` and `copy_group` that only the page reads.
const saved: BankEntry = {
  id: "e1",
  section: "experience",
  custom_section_id: null,
  title: "Software Engineer Intern",
  organization: "Initech",
  location: "Austin, TX",
  start_month: "2025-06",
  end_month: "2025-08",
  end_kind: "month",
  degree: null,
  field_of_study: null,
  gpa: null,
  gpa_scale: null,
  coursework: [],
  honors: null,
  link: null,
  issuer: null,
  award_date: null,
  bullets: [{ id: "b1", position: 0, text: "Built the billing service" }],
  resume_ids: ["r1"],
  copy_group: "experience|software engineer intern|initech|2025-06-01|2025-08-01",
};

test("an edit's PATCH body holds only the fields the PATCH declares", () => {
  assert.deepEqual(Object.keys(changesOf(draftOf(saved))).sort(), [...PATCH_FIELDS].sort());
});

test("a draft that still holds the page's keys saves only the PATCH's fields", () => {
  // Intake keeps its card in localStorage, so a card kept before KAN-505
  // still holds them.
  const kept = { ...saved, bullets: [{ id: "b1", text: "Built the billing service" }] };
  assert.deepEqual(Object.keys(changesOf(kept)).sort(), [...PATCH_FIELDS].sort());
});

test("a draft keeps the entry's fields and bullets, and nothing the page reads", () => {
  const draft = draftOf(saved);
  assert.equal(draft.section, "experience");
  assert.equal(draft.title, "Software Engineer Intern");
  assert.equal(draft.start_month, "2025-06");
  assert.deepEqual(draft.bullets, [{ id: "b1", text: "Built the billing service" }]);
  for (const key of ["id", "resume_ids", "copy_group"]) assert.equal(key in draft, false, key);
});

const savedCustom = {
  ...emptyDraft("custom", "sec-1"),
  id: "e1",
  title: "Tutor",
  bullets: [{ id: "b1", position: 0, text: "Taught math" }],
  resume_ids: ["r1"],
  copy_group: "custom|tutor||None|None",
} as BankEntry<"custom">;

test("a custom entry's PATCH leaves out its section and custom section", () => {
  // The API refuses any other key (EntryUpdate), so the holdings stay out,
  // and the section and its custom section are fixed once saved
  const changes = changesOf(draftOf(savedCustom));
  for (const key of ["id", "bullets", "resume_ids", "copy_group", "section", "custom_section_id"]) {
    assert.ok(!(key in changes), key);
  }
  assert.equal(changes.title, "Tutor");
  // The draft itself keeps its section, so its Save names the right one
  assert.equal(draftOf(savedCustom).custom_section_id, "sec-1");
});

test("a new custom entry names its section; a fixed one names none", () => {
  assert.equal(emptyDraft("custom", "sec-1").custom_section_id, "sec-1");
  assert.equal(emptyDraft("projects").custom_section_id, null);
  assert.equal(isFixed(savedCustom), false);
  assert.equal(isFixed({ ...savedCustom, section: "projects" } as BankEntry), true);
});

test("a row's gaps are badge labels: dates, organization and bullets", () => {
  const job = { ...emptyDraft("experience"), title: "Intern", bullets: [] };
  assert.deepEqual(rowGaps(job), ["Dates", "Company", "Bullets"]);
  // An expected end with no start is the start alone
  const school = {
    ...emptyDraft("education"),
    title: "SBU",
    end_kind: "expected" as const,
    end_month: "2027-05",
    bullets: [],
  };
  assert.deepEqual(rowGaps(school), ["Start Date"]);
  // An award wants neither dates nor bullets
  assert.deepEqual(rowGaps({ ...emptyDraft("awards"), title: "Dean's List", bullets: [] }), []);
  // An empty bullet box is no bullet
  const project = { ...emptyDraft("projects"), title: "Robot", bullets: [{ text: " " }] };
  assert.deepEqual(rowGaps(project), ["Bullets"]);
});
