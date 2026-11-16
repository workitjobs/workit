import assert from "node:assert/strict";
import { test } from "node:test";

import {
  groupSkills,
  likelyDuplicates,
  mergeGroups,
  moveGroup,
  moveSkill,
  orderOf,
  renameGroup,
  sameGroup,
  sameOrder,
  spotOf,
  stepOf,
  type SkillGroup,
} from "./skill-order.ts";

type S = { id: string; name: string; group: string | null };
const skill = (name: string, group: string | null): S => ({ id: name, name, group });

const SKILLS = [
  skill("Python", "Languages"),
  skill("Git", "Tools"),
  skill("Go", "Languages"),
  skill("Bash", null),
];

/** Each group as "Key: a, b" to read a whole arrangement at once. */
const shape = (groups: SkillGroup<S>[]) =>
  groups.map((g) => `${g.label}: ${g.skills.map((s) => s.name).join(", ")}`);

test("groups sit where their first skill is, and no group is Other", () => {
  const groups = groupSkills(SKILLS);
  assert.deepEqual(shape(groups), ["Languages: Python, Go", "Tools: Git", "Other: Bash"]);
  assert.equal(groups[2].key, "");
});

test("a group moves whole; a skill moves within its group or into another", () => {
  const groups = groupSkills(SKILLS);
  assert.deepEqual(shape(moveGroup(groups, 2, 0)), [
    "Other: Bash",
    "Languages: Python, Go",
    "Tools: Git",
  ]);
  assert.deepEqual(shape(moveSkill(groups, { group: 0, at: 1 }, { group: 0, at: 0 })), [
    "Languages: Go, Python",
    "Tools: Git",
    "Other: Bash",
  ]);
  // Git leaves Tools empty, so Tools goes
  assert.deepEqual(shape(moveSkill(groups, { group: 1, at: 0 }, { group: 2, at: 1 })), [
    "Languages: Python, Go",
    "Other: Bash, Git",
  ]);
});

test("an arrow key steps a skill past its group's edge into the next group", () => {
  const groups = groupSkills(SKILLS);
  assert.deepEqual(stepOf(groups, { group: 0, at: 0 }, 1), { group: 0, at: 1 });
  assert.deepEqual(stepOf(groups, { group: 0, at: 1 }, 1), { group: 1, at: 0 });
  // Back into Languages lands at its end, after Go
  assert.deepEqual(stepOf(groups, { group: 1, at: 0 }, -1), { group: 0, at: 2 });
  assert.equal(stepOf(groups, { group: 0, at: 0 }, -1), null);
  assert.equal(stepOf(groups, { group: 2, at: 0 }, 1), null);
});

test("&, and, case and spaces make one name; no group is Other", () => {
  assert.ok(sameGroup("Frameworks & Libraries", "frameworks  and libraries"));
  assert.ok(sameGroup("", "Other"));
  assert.ok(!sameGroup("Tools", "Dev Tools"));
});

test("the likely duplicates are the test account's two pairs", () => {
  const groups = groupSkills([
    skill("React", "Frameworks & Libraries"),
    skill("Make", "Other"),
    skill("Vue", "Frameworks and Libraries"),
    skill("Python", "Languages"),
    skill("Bash", null),
  ]);
  assert.deepEqual(likelyDuplicates(groups), [
    [0, 2],
    [1, 4],
  ]);
  assert.deepEqual(likelyDuplicates(groupSkills(SKILLS)), []);
});

test("a merge keeps the earlier group's place, its skills first, under the name given", () => {
  const groups = groupSkills([
    skill("React", "Frameworks & Libraries"),
    skill("Python", "Languages"),
    skill("Vue", "Frameworks and Libraries"),
  ]);
  const merged = mergeGroups(groups, 2, 0, "Frameworks & Libraries");
  assert.deepEqual(shape(merged), ["Frameworks & Libraries: React, Vue", "Languages: Python"]);
});

test("a rename relabels a group, or merges it into the group of that name", () => {
  const groups = groupSkills([
    skill("React", "Frameworks"),
    skill("Python", "Languages"),
    skill("Vue", "Libraries"),
  ]);
  assert.deepEqual(shape(renameGroup(groups, 2, " Web ")), [
    "Frameworks: React",
    "Languages: Python",
    "Web: Vue",
  ]);
  // The typed name wins, at the earlier group's place
  assert.deepEqual(shape(renameGroup(groups, 2, "frameworks")), [
    "frameworks: React, Vue",
    "Languages: Python",
  ]);
});

test("the save lists every skill in order, each with the copies it stands for", () => {
  const groups = groupSkills(SKILLS);
  const copies: Record<string, S[]> = {
    Python: [skill("Python", "Languages"), skill("py2", "Old")],
  };
  assert.deepEqual(
    orderOf(groups, (s) => copies[s.name] ?? [s]),
    [
      { id: "Python", group: "Languages" },
      { id: "py2", group: "Languages" },
      { id: "Go", group: "Languages" },
      { id: "Git", group: "Tools" },
      { id: "Bash", group: null },
    ],
  );
});

test("a skill is found after a move, and two arrangements compare by order", () => {
  const groups = groupSkills(SKILLS);
  const moved = moveSkill(groups, { group: 0, at: 0 }, { group: 1, at: 1 });
  assert.deepEqual(
    spotOf(moved, (s) => s.id === "Python"),
    { group: 1, at: 1 },
  );
  assert.equal(
    spotOf(moved, (s) => s.id === "Nope"),
    null,
  );
  assert.ok(sameOrder(groups, groupSkills([...SKILLS])));
  assert.ok(!sameOrder(groups, moved));
});
