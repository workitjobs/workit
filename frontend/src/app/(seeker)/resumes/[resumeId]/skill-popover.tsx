"use client";

import { useState } from "react";

import { Popover, PopoverContent, PopoverHeader, PopoverTitle } from "@/components/shadcn/popover";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";

import { PICKED_BLOCK } from "./page-handles";
import { GROUP_MAX, SKILL_MAX } from "./skill-group-dialog";

/**
 * Add a Skill Group (2026-11-23): Technical Skills' heading's + on the
 * page asks for a new line's name and its first skill, in a short form
 * hung from the section's tint, as Delete's confirm hangs from a resume's
 * trash (`DeleteResumeConfirm`), so the question sits where the student
 * clicked and the new line prints right under it. A line's own skills
 * and name are edited in Edit Skill Group (`SkillGroupDialog`), from its
 * six dots; a + on each line came first, and the user chose the dialog.
 *
 * It holds a resume's usual shape as the dialog does: a name at most
 * `GROUP_MAX` characters and never one another line prints, a skill at
 * most `SKILL_MAX`.
 */
export function SkillPopover({
  anchor,
  onClose,
  onAdd,
  taken,
}: {
  /** The + that asked, which gets the focus back. The popover hangs from
   *  the picked section's tint, which stays put while the handle follows
   *  the pointer, and from this when nothing is picked. */
  anchor: HTMLElement;
  onClose: () => void;
  /** Saves a skill into a group on this resume; an error, or null. */
  onAdd: (group: string, name: string) => Promise<string | null>;
  /** Whether a line on this resume prints under this name. */
  taken: (name: string) => boolean;
}) {
  const [group, setGroup] = useState("");
  const [skill, setSkill] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const name = group.trim();
    const typed = skill.trim();
    if (!name) return setError("Name the group.");
    if (taken(name))
      return setError(`${name} is already on this resume. Add the skill there instead.`);
    if (!typed) return setError("Type a skill.");
    setBusy(true);
    const failed = await onAdd(name, typed);
    setBusy(false);
    if (failed) return setError(failed);
    onClose();
  };
  const enter = (event: { key: string; preventDefault: () => void }) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    void submit();
  };

  return (
    <Popover open onOpenChange={(open) => !open && !busy && onClose()}>
      <PopoverContent
        data-keeps-selection
        anchor={{
          getBoundingClientRect: () =>
            (document.querySelector(`[${PICKED_BLOCK}]`) ?? anchor).getBoundingClientRect(),
        }}
        align="start"
        finalFocus={{ current: anchor }}
        className="w-80"
      >
        <PopoverHeader>
          <PopoverTitle className="text-label">Add a Skill Group</PopoverTitle>
        </PopoverHeader>
        <TextField
          id="skill-group-name"
          label="Group Name"
          autoFocus
          value={group}
          maxLength={GROUP_MAX}
          disabled={busy}
          aria-invalid={error ? true : undefined}
          onChange={(event) => {
            setGroup(event.target.value);
            setError(null);
          }}
          onKeyDown={enter}
        />
        <TextField
          id="skill-name"
          label="First Skill"
          value={skill}
          maxLength={SKILL_MAX}
          disabled={busy}
          aria-invalid={error ? true : undefined}
          onChange={(event) => {
            setSkill(event.target.value);
            setError(null);
          }}
          onKeyDown={enter}
        />
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => void submit()} disabled={busy}>
            {busy ? "Adding…" : "Add Group"}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
