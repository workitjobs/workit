"use client";

import { XIcon } from "@phosphor-icons/react/ssr";

import { IconButton } from "@/components/ui/icon-button";

/** A skill as the list needs it: saved on Experiences, or read and not yet
 *  saved in onboarding's resume preview. */
type ListedSkill = { name: string; group: string | null };

/** A skill's purple chip: the card's and the Skills dialog's (KAN-816). */
export const SKILL_CHIP =
  "rounded-control bg-brand-tint text-note text-brand-ink inline-flex items-center gap-1.5 border border-transparent px-2 py-1";

/**
 * Skills as every surface draws them (KAN-732): one row per group, each
 * skill a purple chip. Shared by the Experiences page's Skills card and
 * onboarding's resume preview, so they cannot drift apart: the preview's own
 * chips were grey and in one ungrouped list.
 *
 * The group names make one column where there is room, so every group's
 * skills start at the same edge; on a phone each name sits over its skills.
 * A skill with no group is under "Other". On Experiences it only reads: the
 * Skills dialog edits (KAN-816), since a pencil and × on every chip made the
 * card hard to read. Onboarding's preview has an edit mode (`editable`), in
 * which each chip shows its × (`onRemove`).
 */
export function SkillGroups<T extends ListedSkill>({
  skills,
  keyOf,
  editable = false,
  onRemove,
}: {
  skills: readonly T[];
  /** A key unique in the list: a saved skill's id, a read one's name. */
  keyOf: (skill: T) => string;
  editable?: boolean;
  onRemove?: (skill: T) => void;
}) {
  const groups = new Map<string, T[]>();
  for (const skill of skills) {
    const key = skill.group ?? "";
    groups.set(key, [...(groups.get(key) ?? []), skill]);
  }

  return (
    <dl className="mt-2 grid gap-x-4 gap-y-2 @md/main:grid-cols-[max-content_minmax(0,1fr)]">
      {[...groups].map(([groupName, members]) => (
        <div key={groupName} className="contents">
          <dt className="text-label text-ink-muted @md/main:pt-1">{groupName || "Other"}</dt>
          <dd className="flex flex-wrap gap-2">
            {members.map((skill) => (
              <span key={keyOf(skill)} className={SKILL_CHIP}>
                {skill.name}
                {editable && onRemove && (
                  <IconButton
                    label={`Remove ${skill.name}`}
                    tooltip={false}
                    onClick={() => onRemove(skill)}
                  >
                    <XIcon aria-hidden className="size-3" />
                  </IconButton>
                )}
              </span>
            ))}
          </dd>
        </div>
      ))}
    </dl>
  );
}
