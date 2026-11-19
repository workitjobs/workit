import assert from "node:assert/strict";
import { test } from "node:test";

import type { Bank } from "@/lib/bank-actions";
import type { Choices, RenderBox } from "@/lib/built-resume-actions";

import { bulletsWithNew, moveTo, sectionOrderAfter } from "./model.ts";
import { blockAt, dropAt, HEADING, outlineOf } from "./page-outline.ts";

// Two jobs of two bullets each under Experience, then one school
const bank = {
  entries: [
    {
      id: "e1",
      section: "experience",
      title: "Acme",
      bullets: ["b1", "b2"].map((id, position) => ({ id, text: `Did ${id}`, position })),
    },
    {
      id: "e2",
      section: "experience",
      title: "Initech",
      bullets: ["b3", "b4"].map((id, position) => ({ id, text: `Did ${id}`, position })),
    },
    { id: "s1", section: "education", title: "State U", bullets: [] },
  ],
  skills: [],
  sections: [],
  resumes: [],
} as unknown as Bank;

const choices = {
  entries: ["s1", "e1", "e2"].map((entry_id) => ({
    entry_id,
    shown: true,
    position: entry_id === "e2" ? 1 : 0,
  })),
  bullets: ["b1", "b2", "b3", "b4"].map((bullet_id, i) => ({
    bullet_id,
    shown: true,
    position: i % 2,
  })),
  skills: [],
  variants: [],
} as unknown as Choices;

const ORDER = ["education", "experience", "projects", "skills"];

const box = (item_id: string, kind: string, y0: number, page = 1): RenderBox =>
  ({ item_id, kind, page, x0: 40, x1: 560, y0, y1: y0 + 11, text: "" }) as RenderBox;

// The header, then Education (one row), then Experience: two jobs
const boxes = [
  box("header", "full_name", 30),
  box("s1", "title", 100),
  box("e1", "title", 150),
  box("b1", "bullet", 165),
  box("b2", "bullet", 178),
  box("e2", "title", 200),
  box("b3", "bullet", 215),
  box("b4", "bullet", 228),
];

const outline = outlineOf(boxes, bank, choices, ORDER);
const find = (id: string) => outline.find((b) => b.id === id)!;

test("the outline lists each section, then its entries, each with its bullets", () => {
  assert.deepEqual(
    outline.map((b) => `${b.kind}:${b.id}`),
    [
      "section:education",
      "entry:s1",
      "section:experience",
      "entry:e1",
      "bullet:b1",
      "bullet:b2",
      "entry:e2",
      "bullet:b3",
      "bullet:b4",
    ],
  );
  assert.equal(find("e1").parent, "experience");
  assert.equal(find("b3").parent, "e2");
});

test("a section starts where the block above it ends, its heading included", () => {
  // The header ends at 41; Education's heading sits between it and the school
  assert.deepEqual(find("education").start, { page: 1, y: 41 });
  assert.deepEqual(find("experience").start, { page: 1, y: 111 });
  // An entry spans its fields and its bullets
  assert.deepEqual(find("e1").start, { page: 1, y: 150 });
  assert.deepEqual(find("e1").end, { page: 1, y: 189 });
});

test("a section that opens a page starts a heading's height over its first line", () => {
  const moved = outlineOf(
    boxes.map((b) =>
      ["e1", "b1", "b2", "e2", "b3", "b4"].includes(b.item_id) ? { ...b, page: 2 } : b,
    ),
    bank,
    choices,
    ORDER,
  );
  const experience = moved.find((b) => b.id === "experience")!;
  assert.deepEqual(experience.start, { page: 2, y: 150 - HEADING });
});

test("the deepest block is found under a point: a bullet, else its entry, else the section", () => {
  assert.equal(blockAt(outline, { page: 1, y: 170 }, 792)?.id, "b1");
  assert.equal(blockAt(outline, { page: 1, y: 155 }, 792)?.id, "e1");
  // The heading's room, above the first job
  assert.equal(blockAt(outline, { page: 1, y: 125 }, 792)?.id, "experience");
});

test("a drag lands before the first sibling whose middle is under the pointer", () => {
  const b1 = find("b1");
  // Below b2's middle: b1 lands last, after b2
  assert.equal(dropAt(outline, b1, { page: 1, y: 186 }).to, 1);
  // Above b2's middle: it stays first
  assert.equal(dropAt(outline, b1, { page: 1, y: 170 }).to, 0);
  // An entry moves among entries, its line over the one it lands before
  const drop = dropAt(outline, find("e2"), { page: 1, y: 140 });
  assert.equal(drop.to, 0);
  assert.equal(drop.line.y, 150);
});

test("moveTo renumbers the siblings with the item at its new place", () => {
  assert.deepEqual(moveTo(bank, choices, "bullet", "b1", 1), {
    bullets: [
      { bullet_id: "b2", position: 0 },
      { bullet_id: "b1", position: 1 },
    ],
  });
  assert.deepEqual(moveTo(bank, choices, "entry", "e2", 0), {
    entries: [
      { entry_id: "e2", position: 0 },
      { entry_id: "e1", position: 1 },
    ],
  });
  // Staying put, or past the end, is no change
  assert.equal(moveTo(bank, choices, "bullet", "b1", 0), null);
  assert.equal(moveTo(bank, choices, "bullet", "b1", 5), null);
});

test("a section move keeps the sections that do not print after the ones that do", () => {
  assert.deepEqual(
    sectionOrderAfter(
      ["education", "experience"],
      ["education", "experience", "projects", "custom:x"],
      1,
      0,
    ),
    ["experience", "education", "projects"],
  );
});

test("a bullet typed in on the page lands after its bullet, shown, its entry renumbered", () => {
  const withNew = {
    ...bank,
    entries: bank.entries.map((e) =>
      e.id === "e1" ? { ...e, bullets: [...e.bullets, { id: "b9", text: "New", position: 2 }] } : e,
    ),
  } as Bank;
  assert.deepEqual(bulletsWithNew(withNew, choices, "e1", "b9", "b1"), [
    { bullet_id: "b1", position: 0, shown: true },
    { bullet_id: "b9", position: 1, shown: true },
    { bullet_id: "b2", position: 2, shown: true },
  ]);
  // After a bullet this resume does not show, it lands last
  assert.deepEqual(
    bulletsWithNew(withNew, choices, "e1", "b9", "gone").map((r) => r.bullet_id),
    ["b1", "b2", "b9"],
  );
});
