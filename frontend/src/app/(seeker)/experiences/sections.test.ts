import assert from "node:assert/strict";
import { test } from "node:test";

import type { BankEntry, EntryFields } from "@/lib/bank-actions";

import {
  changesOf,
  draftOf,
  emptyDraft,
  formatDates,
  holdsTools,
  isFixed,
  rowGaps,
  splitList,
  TOOL_COMMA,
  toolsLine,
} from "./sections.ts";

test("only a project holds tools", () => {
  assert.equal(holdsTools("projects"), true);
  assert.equal(holdsTools("experience"), false);
  assert.equal(holdsTools("education"), false);
});

test("a typed list splits at commas, trimmed, with no empty items", () => {
  assert.deepEqual(splitList(" Algorithms,, Operating Systems ,"), [
    "Algorithms",
    "Operating Systems",
  ]);
});

test("tools keep a comma inside parentheses, as the API splits a typed tools line", () => {
  assert.deepEqual(splitList("Next.js, Supabase (PostgreSQL, pgvector), FastAPI", TOOL_COMMA), [
    "Next.js",
    "Supabase (PostgreSQL, pgvector)",
    "FastAPI",
  ]);
});

test("the tools line is the list as the resume prints it, or nothing", () => {
  assert.equal(toolsLine({ tools: ["Next.js", "TypeScript"] }), "Next.js, TypeScript");
  assert.equal(toolsLine({ tools: [] }), null);
});

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
  "tools",
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
  tools: [],
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

test("a date given as a year alone shows as the year (KAN-808)", () => {
  const school = {
    section: "education",
    start_month: "2019-01",
    end_month: "2023-01",
    end_kind: "month",
    year_only: ["start_month", "end_month"],
  } as EntryFields;
  assert.equal(formatDates(school), "2019 – 2023");
  assert.equal(formatDates({ ...school, year_only: ["end_month"] }), "Jan 2019 – 2023");
  assert.equal(formatDates({ ...school, year_only: undefined }), "Jan 2019 – Jan 2023");
  const award = {
    section: "awards",
    award_date: "2024-01",
    year_only: ["award_date"],
  } as EntryFields;
  assert.equal(formatDates(award), "2024");
});
