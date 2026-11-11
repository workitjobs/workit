import assert from "node:assert/strict";
import { test } from "node:test";

import type { Bank } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";

import { reverseChoices } from "./history.ts";
import { arrangeSkills, mergeChoices, moveSkill, printedSkills } from "./model.ts";

// KAN-586: the Sections outline's skill groups, moves and Undo
const skill = (id: string, name: string, group: string | null) => ({
  id,
  name,
  group,
  resume_ids: [],
});
const bank = {
  entries: [],
  sections: [],
  skills: [
    skill("py", "Python", "Languages"),
    skill("ts", "TypeScript", "Languages"),
    skill("re", "React", "Frameworks"),
    skill("fg", "Figma", null),
    skill("go", "Go", "Languages"),
  ],
} as unknown as Bank;

const choices: Choices = {
  entries: [],
  bullets: [],
  variants: [],
  skills: [
    { skill_id: "py", shown: true, position: 0, group: null },
    { skill_id: "ts", shown: true, position: 1, group: null },
    { skill_id: "re", shown: true, position: 2, group: null },
    { skill_id: "fg", shown: true, position: 3, group: null },
    // Hidden: not in the outline, and its position is left alone
    { skill_id: "go", shown: false, position: 4, group: null },
  ],
};

test("skills group as the page prints them, the ungrouped as Other", () => {
  assert.deepEqual(printedSkills(bank, choices), [
    {
      key: "Languages",
      label: "Languages",
      skills: [
        { id: "py", name: "Python" },
        { id: "ts", name: "TypeScript" },
      ],
    },
    { key: "Frameworks", label: "Frameworks", skills: [{ id: "re", name: "React" }] },
    { key: "", label: "Other", skills: [{ id: "fg", name: "Figma" }] },
  ]);
});

test("a skill's group on this resume beats the bank's", () => {
  const moved: Choices = {
    ...choices,
    skills: choices.skills.map((c) => (c.skill_id === "ts" ? { ...c, group: "Frameworks" } : c)),
  };
  const groups = printedSkills(bank, moved);
  assert.deepEqual(
    groups.map((g) => [g.key, g.skills.map((s) => s.id)]),
    [
      ["Languages", ["py"]],
      ["Frameworks", ["ts", "re"]],
      ["", ["fg"]],
    ],
  );
});

test("a move within a group renumbers the shown skills and moves no group", () => {
  const groups = moveSkill(printedSkills(bank, choices), { group: 0, at: 1 }, { group: 0, at: 0 });
  assert.deepEqual(arrangeSkills(bank, choices, groups), {
    skills: [
      { skill_id: "ts", position: 0 },
      { skill_id: "py", position: 1 },
      { skill_id: "re", position: 2 },
      { skill_id: "fg", position: 3 },
    ],
  });
});

test("a move to another group names that group, and the emptied group goes", () => {
  const groups = moveSkill(printedSkills(bank, choices), { group: 1, at: 0 }, { group: 2, at: 1 });
  assert.deepEqual(
    groups.map((g) => g.key),
    ["Languages", ""],
  );
  assert.deepEqual(arrangeSkills(bank, choices, groups), {
    skills: [
      { skill_id: "py", position: 0 },
      { skill_id: "ts", position: 1 },
      { skill_id: "fg", position: 2 },
      { skill_id: "re", position: 3, group: "" },
    ],
  });
});

test("a group dragged whole prints first, with every skill in it", () => {
  const [languages, frameworks, other] = printedSkills(bank, choices);
  assert.deepEqual(arrangeSkills(bank, choices, [frameworks, languages, other]).skills, [
    { skill_id: "re", position: 0 },
    { skill_id: "py", position: 1 },
    { skill_id: "ts", position: 2 },
    { skill_id: "fg", position: 3 },
  ]);
});

test("the move shows at once: its group joins the choices", () => {
  const merged = mergeChoices(choices, { skills: [{ skill_id: "re", position: 3, group: "" }] });
  assert.equal(merged.skills.find((c) => c.skill_id === "re")?.group, "");
});

test("Undo of a move off the bank's group names the bank's group", () => {
  // A null group keeps its value in a save, so the reverse cannot be null
  assert.deepEqual(
    reverseChoices(bank, choices, { skills: [{ skill_id: "re", position: 3, group: "" }] }),
    { skills: [{ skill_id: "re", position: 2, group: "Frameworks" }] },
  );
  // An ungrouped skill goes back to no group
  assert.deepEqual(
    reverseChoices(bank, choices, { skills: [{ skill_id: "fg", group: "Languages" }] }),
    { skills: [{ skill_id: "fg", group: "" }] },
  );
});

test("Undo of a second move puts back the group this resume had", () => {
  const moved: Choices = {
    ...choices,
    skills: choices.skills.map((c) => (c.skill_id === "re" ? { ...c, group: "Tools" } : c)),
  };
  assert.deepEqual(
    reverseChoices(bank, moved, { skills: [{ skill_id: "re", group: "Languages" }] }),
    { skills: [{ skill_id: "re", group: "Tools" }] },
  );
});
