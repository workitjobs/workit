"use client";

import { PencilSimpleIcon, XIcon } from "@phosphor-icons/react/ssr";

import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

/** A skill as the list needs it: saved on Experiences, or read and not yet
 *  saved in onboarding's resume preview. */
type ListedSkill = { name: string; group: string | null };

/**
 * Skills as every surface draws them (KAN-732): one row per group, each
 * skill a purple chip. Shared by the Experiences page's Skills card and
 * onboarding's resume preview, so they cannot drift apart: the preview's own
 * chips were grey and in one ungrouped list.
 *
 * The group names make one column where there is room, so every group's
 * skills start at the same edge; on a phone each name sits over its skills.
 * A skill with no group is under "Other". In edit mode (`editable`) each chip
 * shows its × and, when the surface can rename one (`onEdit`), its pencil
 * (KAN-363); `editing` is the chip open in the surface's form, outlined.
 */
export function SkillGroups<T extends ListedSkill>({
  skills,
  keyOf,
  editable = false,
  editing = null,
  onEdit,
  onRemove,
}: {
  skills: readonly T[];
  /** A key unique in the list: a saved skill's id, a read one's name. */
  keyOf: (skill: T) => string;
  editable?: boolean;
  /** The key of the chip open in the surface's form. */
  editing?: string | null;
  onEdit?: (skill: T) => void;
  onRemove: (skill: T) => void;
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
              <span
                key={keyOf(skill)}
                className={cn(
                  "rounded-control bg-brand-tint text-note text-brand-ink inline-flex items-center gap-1.5 border px-2 py-1",
                  editing === keyOf(skill) ? "border-brand" : "border-transparent",
                )}
              >
                {skill.name}
                {editable && (
                  <>
                    {onEdit && (
                      <IconButton
                        label={`Edit ${skill.name}`}
                        tooltip="Edit this skill"
                        onClick={() => onEdit(skill)}
                      >
                        <PencilSimpleIcon aria-hidden className="size-3" />
                      </IconButton>
                    )}
                    <IconButton
                      label={`Remove ${skill.name}`}
                      tooltip="Remove this skill"
                      onClick={() => onRemove(skill)}
                    >
                      <XIcon aria-hidden className="size-3" />
                    </IconButton>
                  </>
                )}
              </span>
            ))}
          </dd>
        </div>
      ))}
    </dl>
  );
}
