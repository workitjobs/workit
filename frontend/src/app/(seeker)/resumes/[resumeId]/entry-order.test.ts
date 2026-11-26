import assert from "node:assert/strict";
import { test } from "node:test";

import type { BankEntry } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";

import { resumeDraft, writesBank } from "./entry-order.ts";

// KAN-586: the resume editor's entry form opens on this resume's order and
// writes the bank only for a field or a word
const entry = {
  id: "e1",
  section: "experience",
  custom_section_id: null,
  title: "Software Intern",
  organization: "Acme",
  location: null,
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
  resume_ids: [],
  bullets: [
    { id: "b1", text: "Cut load time by 30%", position: 0 },
    { id: "b2", text: "Wrote tests", position: 1 },
    { id: "b3", text: "Fixed a bug", position: 2 },
  ],
} as unknown as BankEntry;

const choices: Choices = {
  entries: [{ entry_id: "e1", shown: true, position: 0, show_gpa: true, show_coursework: true }],
  bullets: [
    { bullet_id: "b1", shown: true, position: 1, variant_id: null, text: null },
    { bullet_id: "b2", shown: false, position: 0, variant_id: null, text: null },
    { bullet_id: "b3", shown: true, position: 0, variant_id: null, text: null },
  ],
  skills: [],
  variants: [],
};

test("the form lists this resume's bullets in its order, then the ones it leaves out", () => {
  assert.deepEqual(resumeDraft(entry, choices).bullets, [
    { id: "b3", text: "Fixed a bug" },
    { id: "b1", text: "Cut load time by 30%" },
    { id: "b2", text: "Wrote tests", off: true },
  ]);
});

test("a bullet with no row on this resume is listed off", () => {
  const none: Choices = { ...choices, bullets: [] };
  assert.ok(resumeDraft(entry, none).bullets.every((b) => b.off));
});

test("a reorder or a box alone never writes the bank", () => {
  const draft = resumeDraft(entry, choices);
  const reordered = {
    ...draft,
    bullets: [...draft.bullets].reverse().map((b) => ({ ...b, off: !b.off })),
  };
  assert.equal(writesBank(entry, reordered), false);
});

test("a changed field, a changed word or a new bullet writes the bank", () => {
  const draft = resumeDraft(entry, choices);
  assert.equal(writesBank(entry, { ...draft, title: "Software Engineer Intern" }), true);
  assert.equal(
    writesBank(entry, {
      ...draft,
      bullets: draft.bullets.map((b) =>
        b.id === "b1" ? { ...b, text: "Cut load time by 40%" } : b,
      ),
    }),
    true,
  );
  assert.equal(
    writesBank(entry, { ...draft, bullets: [...draft.bullets, { text: "Led standups" }] }),
    true,
  );
  // An empty new box is dropped on save, so it writes nothing
  assert.equal(writesBank(entry, { ...draft, bullets: [...draft.bullets, { text: " " }] }), false);
});
