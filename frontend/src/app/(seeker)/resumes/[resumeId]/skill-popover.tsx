"use client";

import { useState } from "react";

import { Popover, PopoverContent, PopoverHeader, PopoverTitle } from "@/components/shadcn/popover";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";

import { PICKED_BLOCK } from "./page-handles";

/**
 * What a skill line's handle asks for on the page (2026-11-23): a skill
 * for a line, a new line with its first skill, or a line's new name. It
 * hangs from the + or the handle that opened it, as Delete's confirm hangs
 * from a resume's trash (`DeleteResumeConfirm`), so the question sits
 * where the student clicked; the page never takes free typing between its
 * words.
 *
 * **The fields hold the page to a resume's usual shape**: a group's name
 * is at most `GROUP_MAX` characters (Tailor's limit on a new group) and a
 * skill's at most `SKILL_MAX`, and a name another line already has is
 * refused, since two lines of one name print as one (`groupKey`).
 */
export type SkillAsk =
  | { kind: "add"; group: string; label: string }
  | { kind: "group" }
  | { kind: "rename"; group: string; label: string };

export const GROUP_MAX = 40;
export const SKILL_MAX = 60;

export function SkillPopover({
  ask,
  anchor,
  onClose,
  onAdd,
  onRename,
  taken,
}: {
  ask: SkillAsk;
  /** The + or handle that asked, which gets the focus back. The popover
   *  hangs from the picked line's tint, which stays put, and from this
   *  when nothing is picked. */
  anchor: HTMLElement;
  onClose: () => void;
  /** Saves a skill into a group on this resume; an error, or null. */
  onAdd: (group: string, name: string) => Promise<string | null>;
  /** Renames a group on this resume. */
  onRename: (group: string, name: string) => void;
  /** Whether another line on this resume prints under this name. */
  taken: (name: string, except?: string) => boolean;
}) {
  const [group, setGroup] = useState(ask.kind === "rename" ? ask.label : "");
  const [skill, setSkill] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title =
    ask.kind === "add"
      ? `Add a Skill to ${ask.label}`
      : ask.kind === "group"
        ? "Add a Skill Group"
        : `Rename ${ask.label}`;
  const act = ask.kind === "add" ? "Add Skill" : ask.kind === "group" ? "Add Group" : "Rename";

  const submit = async () => {
    const name = group.trim();
    const typed = skill.trim();
    if (ask.kind !== "add") {
      if (!name) return setError("Name the group.");
      if (taken(name, ask.kind === "rename" ? ask.label : undefined))
        return setError(
          `${name} is already on this resume. ${ask.kind === "rename" ? "Pick another name." : "Add the skill there instead."}`,
        );
    }
    if (ask.kind === "rename") {
      onRename(ask.group, name);
      return onClose();
    }
    if (!typed) return setError("Type a skill.");
    setBusy(true);
    const failed = await onAdd(ask.kind === "add" ? ask.group : name, typed);
    setBusy(false);
    if (failed) return setError(failed);
    if (ask.kind === "group") return onClose();
    // Ready for the next one, as the Sections outline's field was
    setSkill("");
    setError(null);
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
          <PopoverTitle className="text-label">{title}</PopoverTitle>
        </PopoverHeader>
        {ask.kind !== "add" && (
          <TextField
            id="skill-group-name"
            label="Group Name"
            autoFocus
            value={group}
            maxLength={GROUP_MAX}
            placeholder="Languages"
            disabled={busy}
            aria-invalid={error ? true : undefined}
            onChange={(event) => {
              setGroup(event.target.value);
              setError(null);
            }}
            onKeyDown={enter}
          />
        )}
        {ask.kind !== "rename" && (
          <TextField
            id="skill-name"
            label={ask.kind === "group" ? "First Skill" : "Skill"}
            autoFocus={ask.kind === "add"}
            value={skill}
            maxLength={SKILL_MAX}
            placeholder="Python"
            disabled={busy}
            aria-invalid={error ? true : undefined}
            onChange={(event) => {
              setSkill(event.target.value);
              setError(null);
            }}
            onKeyDown={enter}
          />
        )}
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={onClose} disabled={busy}>
            {ask.kind === "add" ? "Done" : "Cancel"}
          </Button>
          <Button size="sm" onClick={() => void submit()} disabled={busy}>
            {busy ? "Adding…" : act}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
