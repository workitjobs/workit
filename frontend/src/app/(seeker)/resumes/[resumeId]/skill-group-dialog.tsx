"use client";

import { XIcon } from "@phosphor-icons/react/ssr";
import {
  useState,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from "react";

import { Handle, LINE_AFTER, LINE_BEFORE } from "@/components/sortable-list";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { TextField } from "@/components/ui/text-field";
import { cn } from "@/lib/cn";

import { BankDialog, DialogHead } from "../../experiences/entry-dialog";
import { SectionMark } from "../../experiences/section-icons";
import { SKILL_CHIP } from "../../experiences/skill-groups";
import type { PrintedSkillGroup } from "./model";

/** A group's name: at most this long, as Tailor's new groups are. */
export const GROUP_MAX = 40;
/** A skill's name, as the Experiences page's Skills dialog takes it. */
export const SKILL_MAX = 60;

/**
 * Edit Skill Group (2026-11-23): one skill line of this resume, from its
 * six dots' menu on the page. The line's name, its skills as chips in the
 * order they print, each chip its own handle with its ×, and a field that
 * adds a skill, drawn in the Experiences page's Skills dialog's frame and
 * chips (`BankDialog`, `SKILL_CHIP`, KAN-816) so the two read as one tool.
 * The user chose it over a + on each line, which added a skill from a
 * small form beside the line: one place edits a line, the page keeps its
 * six dots and nothing else.
 *
 * **Every change is this resume's, at once, with Undo**, as any edit in the
 * editor: a rename and a reorder are choice changes (`arrangeSkills`), a ×
 * takes the skill off this resume and never out of the bank, and an add
 * shows a skill the bank has or saves a new one for this resume. Taking the
 * last skill off takes the line, and the dialog closes.
 *
 * **It holds a resume's usual shape**: a name at most `GROUP_MAX`
 * characters and never one another line prints (two lines of one name
 * print as one, `groupKey`), a skill at most `SKILL_MAX`.
 */
export function SkillGroupDialog({
  group,
  returnTo,
  onClose,
  onRename,
  onReorder,
  onRemove,
  onAdd,
}: {
  group: PrintedSkillGroup;
  returnTo: RefObject<() => HTMLElement | null>;
  onClose: () => void;
  /** Renames the line on this resume; an error, or null. */
  onRename: (name: string) => string | null;
  /** The line's skills in their new order. */
  onReorder: (skills: PrintedSkillGroup["skills"]) => void;
  /** Takes one skill off this resume. */
  onRemove: (skillId: string) => void;
  /** Puts a skill on this line; an error, or null. */
  onAdd: (name: string) => Promise<string | null>;
}) {
  const [name, setName] = useState(group.label);
  const [skill, setSkill] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragged, setDragged] = useState<number | null>(null);
  // Where the chip would land: before the chip at this index
  const [gap, setGap] = useState<number | null>(null);
  const skills = group.skills;

  const rename = () => {
    const typed = name.trim();
    if (typed === group.label) return;
    if (!typed) {
      setName(group.label);
      return setError("A group needs a name.");
    }
    const failed = onRename(typed);
    setError(failed);
    if (failed) setName(group.label);
  };
  const add = async (event: FormEvent) => {
    event.preventDefault();
    const typed = skill.trim();
    if (!typed) return;
    setBusy(true);
    const failed = await onAdd(typed);
    setBusy(false);
    setError(failed);
    if (!failed) setSkill("");
  };
  const move = (from: number, to: number) => {
    if (from === to || to < 0 || to >= skills.length) return;
    const next = [...skills];
    next.splice(to, 0, ...next.splice(from, 1));
    onReorder(next);
    // The chip remounts at its new place: its handle takes the focus back,
    // so the arrow keys can keep moving it
    requestAnimationFrame(() =>
      document
        .querySelector<HTMLElement>(`[data-handle="${CSS.escape(`skill:${skills[from].id}`)}"]`)
        ?.focus(),
    );
  };
  const end = () => {
    setDragged(null);
    setGap(null);
  };
  const over = (event: DragEvent<HTMLLIElement>, at: number) => {
    if (dragged === null) return;
    event.preventDefault();
    const box = event.currentTarget.getBoundingClientRect();
    setGap(event.clientX < box.left + box.width / 2 ? at : at + 1);
  };
  const drop = (event: DragEvent) => {
    if (dragged === null || gap === null) return;
    event.preventDefault();
    // Taking the chip out moves every later chip back one
    move(dragged, gap > dragged ? gap - 1 : gap);
    end();
  };
  const keys = (event: KeyboardEvent, at: number) => {
    const by =
      event.key === "ArrowLeft" || event.key === "ArrowUp"
        ? -1
        : event.key === "ArrowRight" || event.key === "ArrowDown"
          ? 1
          : 0;
    if (!by) return;
    event.preventDefault();
    move(at, at + by);
  };

  return (
    <BankDialog returnTo={returnTo} onLeave={onClose}>
      <DialogHead
        title={
          <>
            <SectionMark id="skills" />
            Edit Skill Group
          </>
        }
      />
      <div
        data-slot="dialog-scroller"
        className="@container/main flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-none px-4 py-4 sm:px-6"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            rename();
          }}
        >
          <TextField
            id="skill-group-name"
            label="Group Name"
            maxLength={GROUP_MAX}
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setError(null);
            }}
            onBlur={rename}
          />
        </form>
        <section aria-label="Skills" className="flex flex-col gap-2">
          <h3 className="text-label text-ink-muted">Skills</h3>
          <p className="text-note text-ink-meta">
            Drag a skill, or use the arrow keys on it, to change the order.
          </p>
          <ul role="list" className="flex flex-wrap gap-2" onDragOver={(e) => e.preventDefault()}>
            {skills.map((s, at) => (
              <li
                key={s.id}
                onDragOver={(event) => over(event, at)}
                onDrop={drop}
                className={cn(
                  SKILL_CHIP,
                  "relative gap-1 pr-1.5",
                  dragged === at && "opacity-50",
                  dragged !== null && gap === at && LINE_BEFORE,
                  dragged !== null && gap === at + 1 && at === skills.length - 1 && LINE_AFTER,
                )}
              >
                <Handle
                  label={s.name}
                  data={`skill:${s.id}`}
                  className="rounded-xs"
                  onDragStart={() => setDragged(at)}
                  onDragEnd={end}
                  onKeyDown={(event) => keys(event, at)}
                >
                  {s.name}
                </Handle>
                <IconButton
                  label={`Remove ${s.name} from this resume`}
                  tooltip={false}
                  onClick={() => onRemove(s.id)}
                >
                  <XIcon aria-hidden className="size-3" />
                </IconButton>
              </li>
            ))}
          </ul>
        </section>
        <form onSubmit={add} className="flex items-end gap-2">
          <div className="min-w-0 flex-1">
            <TextField
              id="skill-group-add"
              label="Add a Skill"
              maxLength={SKILL_MAX}
              value={skill}
              // Read-only while it saves, not disabled: a disabled field
              // drops the focus, and the next skill is typed straight after
              readOnly={busy}
              onChange={(event) => {
                setSkill(event.target.value);
                setError(null);
              }}
            />
          </div>
          <Button type="submit" variant="secondary" disabled={busy || !skill.trim()}>
            {busy ? "Adding…" : "Add Skill"}
          </Button>
        </form>
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
      </div>
      <div className="border-border-subtle flex shrink-0 justify-end border-t px-4 py-3 sm:px-6">
        <Button onClick={onClose}>Done</Button>
      </div>
    </BankDialog>
  );
}
