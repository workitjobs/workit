/**
 * The Skills dialog's groups (KAN-816), pure: the skills as groups, each
 * change the dialog makes (a move, a rename, a merge), the groups that are
 * likely one, and the API's body for the save (`orderSkills`). The dialog
 * draws them (`skills-dialog.tsx`); the API keeps the order
 * (`bank_skills.position`).
 *
 * A group is a name the student's skills share, saved on each skill, so a
 * group with no skill does not exist: a move that empties one drops it. A
 * skill with no group is in "Other" (`key` ""), as on the card.
 */

export type SkillGroup<T> = {
  /** The name saved on its skills, "" for none. */
  key: string;
  /** What shows: the name, or "Other". */
  label: string;
  skills: T[];
};

/** Where a skill sits: its group's index, and its index in the group. */
export type Spot = { group: number; at: number };

const labelOf = (key: string) => key || "Other";

/** The skills as groups, each where its first skill is: the bank's order. */
export function groupSkills<T extends { group: string | null }>(
  skills: readonly T[],
): SkillGroup<T>[] {
  const groups = new Map<string, SkillGroup<T>>();
  for (const skill of skills) {
    const key = skill.group ?? "";
    if (!groups.has(key)) groups.set(key, { key, label: labelOf(key), skills: [] });
    groups.get(key)!.skills.push(skill);
  }
  return [...groups.values()];
}

/** A group moved from one place to another. */
export function moveGroup<T>(groups: SkillGroup<T>[], from: number, to: number): SkillGroup<T>[] {
  const next = [...groups];
  next.splice(to, 0, ...next.splice(from, 1));
  return next;
}

/** A skill moved within its group or into another; a group it leaves
 *  empty goes. */
export function moveSkill<T>(groups: SkillGroup<T>[], from: Spot, to: Spot): SkillGroup<T>[] {
  const next = groups.map((g) => ({ ...g, skills: [...g.skills] }));
  const [moved] = next[from.group].skills.splice(from.at, 1);
  next[to.group].skills.splice(to.at, 0, moved);
  return next.filter((g) => g.skills.length > 0);
}

/** Where an arrow key takes a skill: one step back or on in its group, and
 *  past a group's edge to the end of the group before or the start of the
 *  one after. Null at either end of the list. */
export function stepOf<T>(groups: SkillGroup<T>[], from: Spot, by: -1 | 1): Spot | null {
  const size = groups[from.group].skills.length;
  if (by < 0) {
    if (from.at > 0) return { group: from.group, at: from.at - 1 };
    if (from.group > 0) return { group: from.group - 1, at: groups[from.group - 1].skills.length };
    return null;
  }
  if (from.at < size - 1) return { group: from.group, at: from.at + 1 };
  if (from.group < groups.length - 1) return { group: from.group + 1, at: 0 };
  return null;
}

/** Two group names that likely mean one group: the same, ignoring case,
 *  spaces and "&" against "and"; no group reads as "Other". */
export function sameGroup(a: string, b: string): boolean {
  return foldName(a) === foldName(b);
}

function foldName(key: string): string {
  return (key || "Other").toLowerCase().replace(/&/g, " and ").replace(/\s+/g, " ").trim();
}

/** The group whose name is `name` once folded, other than `besides`: the
 *  one a rename to that name joins. */
export function groupNamed<T>(groups: SkillGroup<T>[], name: string, besides: number): number {
  return groups.findIndex((g, i) => i !== besides && sameGroup(g.key, name));
}

/**
 * Two groups made one: both groups' skills, the earlier group's first, under
 * `key`, where the earlier group was. A rename to another group's name merges
 * this way, with the name typed; the duplicates notice's Merge, with the
 * earlier group's name.
 */
export function mergeGroups<T>(
  groups: SkillGroup<T>[],
  a: number,
  b: number,
  key: string,
): SkillGroup<T>[] {
  const [first, second] = a < b ? [a, b] : [b, a];
  const merged = {
    key,
    label: labelOf(key),
    skills: [...groups[first].skills, ...groups[second].skills],
  };
  return groups.flatMap((g, i) => (i === first ? [merged] : i === second ? [] : [g]));
}

/** A group renamed; a name another group has (`groupNamed`) merges the two. */
export function renameGroup<T>(groups: SkillGroup<T>[], at: number, name: string): SkillGroup<T>[] {
  const key = name.trim();
  const other = groupNamed(groups, key, at);
  if (other >= 0) return mergeGroups(groups, at, other, key);
  return groups.map((g, i) => (i === at ? { ...g, key, label: labelOf(key) } : g));
}

/** The pairs of groups that are likely one (`sameGroup`), each pair in
 *  list order: the test account had "Frameworks & Libraries" beside
 *  "Frameworks and Libraries", and two "Other" groups. */
export function likelyDuplicates<T>(groups: SkillGroup<T>[]): [number, number][] {
  const pairs: [number, number][] = [];
  groups.forEach((g, i) => {
    const j = groups.findIndex((h, k) => k > i && sameGroup(g.key, h.key));
    // Only the next one: a third of the same name pairs with the second
    if (j >= 0) pairs.push([i, j]);
  });
  return pairs;
}

/** A skill's place once groups and skills move: its group and its index in
 *  it, or null when it is gone. */
export function spotOf<T>(groups: SkillGroup<T>[], match: (skill: T) => boolean): Spot | null {
  for (const [group, g] of groups.entries()) {
    const at = g.skills.findIndex(match);
    if (at >= 0) return { group, at };
  }
  return null;
}

/** The API's body: every skill in its order, in its group (null for none),
 *  each followed by the copies it stands for (`copiesOf`: under All
 *  Experiences a chip is every copy of its name, ADR 0005). */
export function orderOf<T extends { id: string }>(
  groups: SkillGroup<T>[],
  copiesOf: (skill: T) => T[],
): { id: string; group: string | null }[] {
  return groups.flatMap((g) =>
    g.skills.flatMap((skill) =>
      [skill, ...copiesOf(skill).filter((c) => c.id !== skill.id)].map((s) => ({
        id: s.id,
        group: g.key || null,
      })),
    ),
  );
}

/** Whether two lists of groups hold the same groups and skills in the same
 *  order: the bank read back matches what the dialog drew. */
export function sameOrder<T extends { id: string }>(a: SkillGroup<T>[], b: SkillGroup<T>[]) {
  const words = (groups: SkillGroup<T>[]) =>
    JSON.stringify(groups.map((g) => [g.key, g.skills.map((s) => s.id)]));
  return words(a) === words(b);
}
