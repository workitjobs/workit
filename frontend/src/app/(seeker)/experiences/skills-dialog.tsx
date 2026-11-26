"use client";

import { PencilSimpleIcon, PlusIcon, TrashIcon, XIcon } from "@phosphor-icons/react/ssr";
import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from "react";

import { EllipsisIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Handle, LINE_AFTER, LINE_BEFORE, SortableList } from "@/components/sortable-list";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Notice } from "@/components/ui/notice";
import { TextField, TextInput } from "@/components/ui/text-field";
import {
  addSkill,
  deleteSkills,
  orderSkills,
  type BankResume,
  type Skill,
} from "@/lib/bank-actions";
import { cn } from "@/lib/cn";

import { clearAllWords } from "./clear-all";
import { BankDialog, ConfirmBar, DialogHead, useFocusOnClose } from "./entry-dialog";
import { ALL, skillCopies, skillRows, type Pick } from "./holdings";
import { SECTION_ICONS, SectionMark } from "./section-icons";
import { SKILL_CHIP } from "./skill-groups";
import {
  groupNamed,
  groupSkills,
  likelyDuplicates,
  mergeGroups,
  moveGroup,
  moveSkill,
  orderOf,
  renameGroup,
  stepOf,
  type SkillGroup,
  type Spot,
} from "./skill-order";

/**
 * Edit Skills (KAN-816), in the frame every other section edits in
 * (`BankDialog`, KAN-740): each group a row with its handle, name, + (a
 * skill into it), pencil (Rename) and trash (Delete Group), its skills as
 * chips under it, each chip its own handle with its ×. A group drags whole,
 * a chip within its group or into another, and each handle's arrow keys do
 * the same (a chip's step past its group's edge into the next group, as the
 * editor's Sections panel does). The card on the page only reads: its
 * pencil and × on every chip, an edit mode of the card's own, went with
 * this.
 *
 * **A rename to another group's name merges the two**, and two groups whose
 * names are likely one ("Frameworks & Libraries" and "Frameworks and
 * Libraries", or a group named Other beside the skills with none) get a
 * notice with Merge: one press, the earlier group's name and place.
 *
 * **Every change shows at once and saves behind it, one at a time**: a move,
 * a rename or a merge is one call that sends the whole order
 * (`orderSkills`, `bank_skills.position`), a × deletes, + adds, in the order
 * made, and once none is left the bank is read back. A failed one shows its
 * message, and the read-back puts the list back as the bank has it. Nothing
 * closes while a save runs, as in the entry form. Delete Group and Clear All
 * ask first across the foot (`ConfirmBar`) and wait for the API, as Clear
 * All always has.
 *
 * Under All Experiences a chip stands for every copy of its name (ADR 0005:
 * two uploads can each hold "Python"), so a move, a rename and a delete take
 * every copy with it; under a resume's pick, the skills that resume shows.
 */
export function SkillsDialog({
  skills,
  pick,
  resumeId,
  resumes,
  adding: addingAtFirst,
  reload,
  returnTo,
  onClose,
}: {
  /** Every skill the pick shows, all copies, not narrowed by a search. */
  skills: Skill[];
  pick: Pick;
  /** The picked resume: a skill added here goes into it. */
  resumeId: string | undefined;
  /** For Clear All's and Delete Group's questions. */
  resumes: BankResume[];
  /** Opened from the card's +: the add form is open. */
  adding: boolean;
  reload: () => Promise<string | null>;
  returnTo: RefObject<() => HTMLElement | null>;
  onClose: () => void;
}) {
  const uid = useId();
  const rows = skillRows(pick, skills);
  const copies = new Map(skillCopies(skills).map((all) => [all[0].id, all]));
  const copiesOf = (skill: Skill) => (pick === ALL ? (copies.get(skill.id) ?? [skill]) : [skill]);
  const base = groupSkills(rows);

  // What the dialog draws while saves run: the change made, ahead of the bank
  const [draft, setDraft] = useState<SkillGroup<Skill>[] | null>(null);
  const groups = draft ?? base;
  // The groups as last drawn or changed, and the copies, for a save that
  // runs after later changes
  const shown = useRef(groups);
  const copiesRef = useRef(copiesOf);
  useLayoutEffect(() => {
    shown.current = groups;
    copiesRef.current = copiesOf;
  });

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(addingAtFirst);
  // The one group with a field open: its Rename, or its + (a skill into it)
  const [field, setField] = useState<{ kind: "rename" | "add"; key: string } | null>(null);
  const [asking, setAsking] = useState<
    { kind: "group"; key: string } | { kind: "clear" } | { kind: "discard"; go: () => void } | null
  >(null);
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  // Typing a field holds, so a way out asks before it drops it
  const typed = useRef(false);
  const focusBackRef = useFocusOnClose(asking !== null);

  // Where the focus lands once a change is drawn (a moved handle, a merged
  // group's pencil). In the commit itself, as every focus move in the
  // bank's dialogs: a move one frame late lost to the dialog's own
  const land = useRef<string | null>(null);
  useLayoutEffect(() => {
    const at = land.current;
    if (!at) return;
    land.current = null;
    document.querySelector<HTMLElement>(`[data-slot=dialog-content] ${at}`)?.focus();
  });
  const landOn = (attr: string, value: string) => {
    land.current = `[${attr}="${CSS.escape(value)}"]`;
  };

  // The saves, one at a time, in the order made; the order's save waits
  // in line once, and sends the groups as they are when its turn comes
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const waiting = useRef(0);
  const orderInLine = useRef(false);

  function enqueue(task: () => Promise<string | null>): Promise<string | null> {
    waiting.current += 1;
    setBusy(true);
    const run = () => task().catch(() => "Your change didn't save. Try again.");
    const done = chain.current.then(run).then(async (failed) => {
      waiting.current -= 1;
      if (waiting.current > 0) return failed;
      const reloadError = await reload();
      if (reloadError) setError(reloadError);
      // Nothing more came in while it read: the bank is what was drawn
      if (waiting.current === 0) {
        setDraft(null);
        setBusy(false);
      }
      return failed;
    });
    chain.current = done;
    return done;
  }

  function change(next: SkillGroup<Skill>[]) {
    shown.current = next;
    setDraft(next);
    setError(null);
  }

  /** Draws the groups and saves their order. */
  function arrange(next: SkillGroup<Skill>[]) {
    change(next);
    if (orderInLine.current) return;
    orderInLine.current = true;
    void enqueue(async () => {
      orderInLine.current = false;
      const order = orderOf(shown.current, copiesRef.current);
      if (order.length === 0) return null;
      const { error } = await orderSkills(order);
      if (error) setError(error);
      return error;
    });
  }

  /** Adds a skill into a group, by name, ignoring case and "&" for "and",
   *  so "languages" goes into Languages; an error, or null. */
  function add(name: string, group: string): Promise<string | null> {
    const at = groupNamed(shown.current, group, -1);
    const key = at >= 0 ? shown.current[at].key : group.trim();
    return enqueue(async () => {
      const res = await addSkill(name.trim(), key || null, resumeId);
      if (!res.data) return res.error ?? "Your skill didn't save. Try again.";
      const created = res.data;
      // At its group's end, or a new group at the end, and saved there
      const now = shown.current;
      const into = now.findIndex((g) => g.key === key);
      arrange(
        into >= 0
          ? now.map((g, i) => (i === into ? { ...g, skills: [...g.skills, created] } : g))
          : [...now, { key, label: key || "Other", skills: [created] }],
      );
      return null;
    });
  }

  function removeSkill(from: Spot) {
    const group = groups[from.group];
    const skill = group.skills[from.at];
    const next = groups
      .map((g, i) => (i === from.group ? { ...g, skills: g.skills.filter((s) => s !== skill) } : g))
      .filter((g) => g.skills.length > 0);
    // The chip after it, else the one before; a group it empties goes, so
    // then the next group's handle, else the one before, else the +
    const near = group.skills[from.at + 1] ?? group.skills[from.at - 1];
    const nextGroup = groups[from.group + 1] ?? groups[from.group - 1];
    if (near) landOn("data-handle", `skill:${near.id}`);
    else if (nextGroup) landOn("data-handle", `group:${nextGroup.key}`);
    else land.current = "#skills-dialog-add";
    change(next);
    const ids = copiesOf(skill).map((s) => s.id);
    void enqueue(async () => {
      const { error } = await deleteSkills(ids);
      if (error) setError(error);
      return error;
    });
  }

  async function act() {
    if (!asking || asking.kind === "discard") return;
    const doomed =
      asking.kind === "clear"
        ? groups.flatMap((g) => g.skills)
        : (groups.find((g) => g.key === asking.key)?.skills ?? []);
    const ids = doomed.flatMap((s) => copiesOf(s).map((c) => c.id));
    setAskBusy(true);
    setAskError(null);
    const failed = await enqueue(async () => {
      const { error } = await deleteSkills(ids);
      if (error) return error;
      // A save still in line sends the groups without them
      if (asking.kind === "group") {
        shown.current = shown.current.filter((g) => g.key !== asking.key);
        setDraft((d) => d && d.filter((g) => g.key !== asking.key));
      }
      return null;
    });
    setAskBusy(false);
    if (failed) return setAskError(failed);
    if (asking.kind === "clear") return onClose();
    const at = groups.findIndex((g) => g.key === asking.key);
    const near = groups[at + 1] ?? groups[at - 1];
    land.current = near
      ? `[data-handle="${CSS.escape(`group:${near.key}`)}"]`
      : "#skills-dialog-add";
    setAsking(null);
  }

  /** Escape, the ×, a press outside: a question already asked gets its safe
   *  answer; Escape closes an open field; typing asks first; a save running
   *  keeps it open. */
  function leave(reason: "escape" | "close" | "outside") {
    if (asking) {
      if (!askBusy) setAsking(null);
      return;
    }
    if (reason === "escape" && field) return closeField();
    if (reason === "escape" && adding) return closeAdd();
    if (busy) return;
    if (typed.current) {
      const was = document.activeElement;
      focusBackRef.current = () => (was instanceof HTMLElement && was.isConnected ? was : null);
      return setAsking({ kind: "discard", go: onClose });
    }
    onClose();
  }

  function closeField() {
    if (field) landOn(field.kind === "rename" ? "data-group-rename" : "data-group-add", field.key);
    typed.current = false;
    setField(null);
  }

  function closeAdd() {
    land.current = "#skills-dialog-add";
    typed.current = false;
    setAdding(false);
  }

  const duplicates = likelyDuplicates(groups);
  const count = groups.reduce((n, g) => n + g.skills.length, 0);

  return (
    <BankDialog returnTo={returnTo} onLeave={leave}>
      <DialogHead
        title={
          <>
            <SectionMark id="skills" />
            Skills
          </>
        }
        description={
          busy
            ? "Saving…"
            : `${count} ${count === 1 ? "skill" : "skills"} in ${groups.length} ${groups.length === 1 ? "group" : "groups"}`
        }
        actions={
          <>
            <IconButton
              place="heading"
              id="skills-dialog-add"
              label="Add Skill"
              tooltip="Add a skill"
              onClick={() => {
                setField(null);
                // Already open: back to its first field (it autofocuses
                // when it opens)
                document.getElementById(`${uid}-skill`)?.focus();
                setAdding(true);
              }}
            >
              <PlusIcon aria-hidden />
            </IconButton>
            {/* Clear All belongs to one resume's view: under All
                Experiences a chip is every copy of its name */}
            {pick !== ALL && count > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <IconButton
                      place="heading"
                      id="skills-dialog-more"
                      label="More actions for Skills"
                      tooltip={false}
                    >
                      <EllipsisIcon />
                    </IconButton>
                  }
                />
                <DropdownMenuContent align="end" className="w-44">
                  <DropdownMenuItem
                    variant="destructive"
                    onClick={() => {
                      setAskError(null);
                      focusBackRef.current = () => document.getElementById("skills-dialog-more");
                      setAsking({ kind: "clear" });
                    }}
                  >
                    <TrashIcon aria-hidden className="size-4" />
                    Clear All
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </>
        }
      />
      <div
        data-slot="dialog-scroller"
        className="@container/main min-h-0 flex-1 overflow-y-auto overscroll-none px-4 sm:px-6"
      >
        {adding && (
          <AddForm uid={uid} onTyped={(on) => (typed.current = on)} add={add} onDone={closeAdd} />
        )}
        {duplicates.map(([a, b]) => (
          <Notice
            key={`${groups[a].key}|${groups[b].key}`}
            Icon={SECTION_ICONS.skills}
            className="mt-4"
            actions={
              <Button
                variant="section"
                aria-label={`Merge ${groups[b].label} into ${groups[a].label}`}
                onClick={() => {
                  landOn("data-group-rename", groups[a].key);
                  arrange(mergeGroups(groups, a, b, groups[a].key));
                }}
              >
                Merge
              </Button>
            }
          >
            {groups[a].label === groups[b].label ? (
              // A group named Other beside the skills with none
              <>You have two groups named &ldquo;{groups[a].label}&rdquo;.</>
            ) : (
              <>
                &ldquo;{groups[a].label}&rdquo; and &ldquo;{groups[b].label}&rdquo; look like one
                group.
              </>
            )}
          </Notice>
        ))}
        {groups.length === 0 ? (
          <p className="text-body text-ink-meta py-4">Nothing here yet.</p>
        ) : (
          <>
            <p className="text-note text-ink-meta mt-4">
              Drag a group or a skill to move it, or use the arrow keys.
            </p>
            <SkillGroupList
              groups={groups}
              field={field}
              onArrange={arrange}
              onLand={landOn}
              onRemove={removeSkill}
              onOpenField={(kind, key) => {
                setAdding(false);
                typed.current = false;
                setField({ kind, key });
              }}
              onCloseField={closeField}
              onTyped={(on) => (typed.current = on)}
              onRename={(at, name) => {
                typed.current = false;
                setField(null);
                const next = renameGroup(groups, at, name);
                landOn("data-group-rename", name.trim());
                if (name.trim() !== groups[at].key) arrange(next);
              }}
              onAdd={add}
              onDelete={(key) => {
                setAskError(null);
                focusBackRef.current = () =>
                  document.querySelector<HTMLElement>(`[data-group-delete="${CSS.escape(key)}"]`);
                setAsking({ kind: "group", key });
              }}
            />
          </>
        )}
        {error && (
          <p role="alert" className="text-note text-danger py-3">
            {error}
          </p>
        )}
      </div>
      {asking && (
        <div className="border-border-subtle shrink-0 border-t px-4 py-3 sm:px-6">
          {asking.kind === "discard" ? (
            <ConfirmBar
              question="Discard Your Changes?"
              keepLabel="Keep Editing"
              actLabel="Discard Changes"
              onKeep={() => setAsking(null)}
              onAct={asking.go}
            >
              You have typing you haven&apos;t saved. If you leave now, it&apos;s lost.
            </ConfirmBar>
          ) : (
            <ConfirmBar
              {...question(asking, groups, copiesOf, resumes, pick)}
              busy={askBusy}
              error={askError}
              onKeep={() => setAsking(null)}
              onAct={act}
            />
          )}
        </div>
      )}
    </BankDialog>
  );
}

/** Delete Group's and Clear All's question: what goes, and where from. */
function question(
  asking: { kind: "group"; key: string } | { kind: "clear" },
  groups: SkillGroup<Skill>[],
  copiesOf: (skill: Skill) => Skill[],
  resumes: BankResume[],
  pick: Pick,
) {
  const shownSkills =
    asking.kind === "clear"
      ? groups.flatMap((g) => g.skills)
      : (groups.find((g) => g.key === asking.key)?.skills ?? []);
  const items = shownSkills.flatMap(copiesOf);
  const words = clearAllWords({ items, resumes, noun: ["skill", "skills"], pick });
  if (asking.kind === "clear") {
    return { question: words.question, children: words.detail, actLabel: "Clear All" };
  }
  const label = groups.find((g) => g.key === asking.key)?.label ?? "";
  const n = shownSkills.length;
  return {
    question: `Delete ${label}?`,
    children: `${n === 1 ? "Its 1 skill goes" : `Its ${n} skills go`} with it. ${words.detail}`,
    actLabel: "Delete Group",
  };
}

/** The head's +: a skill and its group, as the card's form was. It stays
 *  open after an add, ready for the next skill in the same group. */
function AddForm({
  uid,
  add,
  onDone,
  onTyped,
}: {
  uid: string;
  add: (name: string, group: string) => Promise<string | null>;
  onDone: () => void;
  onTyped: (typed: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [group, setGroup] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameField = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    const failed = await add(name, group);
    setBusy(false);
    if (failed) return setError(failed);
    setError(null);
    setName("");
    onTyped(false);
    nameField.current?.focus();
  }

  return (
    <form
      onSubmit={submit}
      className="border-border-subtle grid items-end gap-3 border-b py-4 @lg/main:grid-cols-[1fr_1fr_auto]"
    >
      <TextField
        ref={nameField}
        id={`${uid}-skill`}
        label="Skill"
        required
        autoFocus
        maxLength={60}
        placeholder="Python"
        value={name}
        // Read-only while it saves, not disabled: a disabled field drops the
        // focus, and the next skill is typed straight after
        readOnly={busy}
        onChange={(e) => {
          setName(e.target.value);
          onTyped(e.target.value.trim() !== "");
        }}
      />
      <TextField
        id={`${uid}-group`}
        label="Group"
        maxLength={60}
        placeholder="Languages"
        value={group}
        readOnly={busy}
        onChange={(e) => setGroup(e.target.value)}
      />
      <div className="flex gap-2">
        <Button type="button" variant="secondary" onClick={onDone}>
          Done
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? "Adding…" : "Add Skill"}
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-note text-danger @lg/main:col-span-3">
          {error}
        </p>
      )}
    </form>
  );
}

/**
 * The groups as rows (`SortableList`, the editor's Sections panel's), each
 * with its chips. One drag for every chip, since a chip crosses groups; a
 * group's own drag is the list's.
 */
function SkillGroupList({
  groups,
  field,
  onArrange,
  onLand,
  onRemove,
  onOpenField,
  onCloseField,
  onTyped,
  onRename,
  onAdd,
  onDelete,
}: {
  groups: SkillGroup<Skill>[];
  field: { kind: "rename" | "add"; key: string } | null;
  onArrange: (next: SkillGroup<Skill>[]) => void;
  /** Where the focus goes once the change is drawn. */
  onLand: (attr: string, value: string) => void;
  onRemove: (from: Spot) => void;
  onOpenField: (kind: "rename" | "add", key: string) => void;
  onCloseField: () => void;
  onTyped: (typed: boolean) => void;
  onRename: (at: number, name: string) => void;
  onAdd: (name: string, group: string) => Promise<string | null>;
  onDelete: (key: string) => void;
}) {
  const [dragged, setDragged] = useState<Spot | null>(null);
  // Where the chip would land: before the chip at this index of its group
  const [gap, setGap] = useState<Spot | null>(null);
  const end = () => {
    setDragged(null);
    setGap(null);
  };

  const move = (from: Spot, to: Spot, id: string) => {
    if (from.group === to.group && from.at === to.at) return;
    // The chip remounts in its new group: its handle takes the focus back,
    // so the arrow keys can keep moving it
    onLand("data-handle", `skill:${id}`);
    onArrange(moveSkill(groups, from, to));
  };
  const drop = (event: DragEvent) => {
    if (dragged === null || gap === null) return;
    event.preventDefault();
    event.stopPropagation();
    // Taking the chip out moves every later chip in its group back one
    const at = gap.group === dragged.group && gap.at > dragged.at ? gap.at - 1 : gap.at;
    move(dragged, { group: gap.group, at }, groups[dragged.group].skills[dragged.at].id);
    end();
  };
  const overChip = (event: DragEvent<HTMLLIElement>, group: number, at: number) => {
    if (dragged === null) return;
    event.preventDefault();
    event.stopPropagation();
    const box = event.currentTarget.getBoundingClientRect();
    setGap({ group, at: event.clientX < box.left + box.width / 2 ? at : at + 1 });
  };
  // Over a group but no chip: the chip goes to the group's end
  const overGroup = (event: DragEvent<HTMLDivElement>, group: number) => {
    if (dragged === null) return;
    event.preventDefault();
    event.stopPropagation();
    setGap({ group, at: groups[group].skills.length });
  };
  const keys = (event: KeyboardEvent, from: Spot, id: string) => {
    const by =
      event.key === "ArrowLeft" || event.key === "ArrowUp"
        ? -1
        : event.key === "ArrowRight" || event.key === "ArrowDown"
          ? 1
          : 0;
    if (!by) return;
    event.preventDefault();
    const to = stepOf(groups, from, by);
    if (to) move(from, to, id);
  };

  return (
    <SortableList
      items={groups}
      idOf={(group) => `group:${group.key}`}
      labelOf={(group) => group.label}
      dataOf={(group) => `group:${group.key}`}
      className="divide-border-subtle mt-1 divide-y"
      onMove={(from, to) => {
        onLand("data-handle", `group:${groups[from].key}`);
        onArrange(moveGroup(groups, from, to));
      }}
      row={(group, handle) => {
        const g = groups.indexOf(group);
        const renaming = field?.kind === "rename" && field.key === group.key;
        const addingHere = field?.kind === "add" && field.key === group.key;
        return (
          <div className="py-3" onDragOver={(event) => overGroup(event, g)} onDrop={drop}>
            {renaming ? (
              <RenameGroup
                groups={groups}
                at={g}
                onTyped={onTyped}
                onSave={(name) => onRename(g, name)}
                onCancel={onCloseField}
              />
            ) : (
              <div className="flex items-center gap-1">
                {handle}
                <h3 className="text-label text-ink min-w-0 flex-1 truncate font-semibold">
                  {group.label}
                  <span className="text-ink-meta font-normal"> · {group.skills.length}</span>
                </h3>
                <IconButton
                  place="row"
                  data-group-add={group.key}
                  label={`Add a skill to ${group.label}`}
                  tooltip="Add a skill"
                  onClick={() => onOpenField("add", group.key)}
                >
                  <PlusIcon aria-hidden />
                </IconButton>
                <IconButton
                  place="row"
                  data-group-rename={group.key}
                  label={`Rename ${group.label}`}
                  tooltip={false}
                  onClick={() => onOpenField("rename", group.key)}
                >
                  <PencilSimpleIcon aria-hidden />
                </IconButton>
                <IconButton
                  place="row"
                  data-group-delete={group.key}
                  label={`Delete ${group.label}`}
                  tooltip={false}
                  onClick={() => onDelete(group.key)}
                >
                  <TrashIcon aria-hidden />
                </IconButton>
              </div>
            )}
            <ul role="list" className="mt-2 flex flex-wrap gap-2 pl-6">
              {group.skills.map((skill, at) => {
                const target = dragged !== null && gap?.group === g;
                return (
                  <li
                    key={skill.id}
                    onDragOver={(event) => overChip(event, g, at)}
                    onDrop={drop}
                    className={cn(
                      SKILL_CHIP,
                      "relative gap-1 pr-1.5",
                      dragged?.group === g && dragged.at === at && "opacity-50",
                      target && gap.at === at && LINE_BEFORE,
                      target && gap.at === at + 1 && at === group.skills.length - 1 && LINE_AFTER,
                    )}
                  >
                    <Handle
                      label={skill.name}
                      data={`skill:${skill.id}`}
                      className="rounded-xs"
                      onDragStart={() => setDragged({ group: g, at })}
                      onDragEnd={end}
                      onKeyDown={(event) => keys(event, { group: g, at }, skill.id)}
                    >
                      {skill.name}
                    </Handle>
                    <IconButton
                      label={`Remove ${skill.name}`}
                      tooltip={false}
                      onClick={() => onRemove({ group: g, at })}
                    >
                      <XIcon aria-hidden className="size-3" />
                    </IconButton>
                  </li>
                );
              })}
              {addingHere && (
                <li>
                  <AddToGroup
                    group={group}
                    onTyped={onTyped}
                    onAdd={(name) => onAdd(name, group.key)}
                    onClose={onCloseField}
                  />
                </li>
              )}
            </ul>
          </div>
        );
      }}
    />
  );
}

/** A group's new name, typed in its heading's place, as a custom section's
 *  Rename is (`RenameSection`). A name another group has merges the two, and
 *  the form says so before it saves. */
function RenameGroup({
  groups,
  at,
  onTyped,
  onSave,
  onCancel,
}: {
  groups: SkillGroup<Skill>[];
  at: number;
  onTyped: (typed: boolean) => void;
  onSave: (name: string) => void;
  onCancel: () => void;
}) {
  const uid = useId();
  const group = groups[at];
  const [name, setName] = useState(group.key);
  const joins = name.trim() ? groupNamed(groups, name, at) : -1;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || name.trim() === group.key) return onCancel();
    onSave(name);
  }

  return (
    <form onSubmit={submit} className="flex w-full flex-col gap-2">
      <TextField
        id={`${uid}-name`}
        label="Group Name"
        required
        maxLength={60}
        autoFocus
        value={name}
        aria-describedby={joins >= 0 ? `${uid}-joins` : undefined}
        onChange={(e) => {
          setName(e.target.value);
          onTyped(e.target.value.trim() !== group.key);
        }}
      />
      {joins >= 0 && (
        <p id={`${uid}-joins`} className="text-note text-ink-meta">
          {groups[joins].label} has this name, so the two groups become one.
        </p>
      )}
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">{joins >= 0 ? "Merge Groups" : "Save Name"}</Button>
      </div>
    </form>
  );
}

/** A group's +: a field after its chips. Enter adds the skill into this
 *  group and leaves the field open for the next; Escape, or leaving it
 *  empty, closes it. */
function AddToGroup({
  group,
  onAdd,
  onClose,
  onTyped,
}: {
  group: SkillGroup<Skill>;
  onAdd: (name: string) => Promise<string | null>;
  onClose: () => void;
  onTyped: (typed: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const field = useRef<HTMLInputElement>(null);

  async function save() {
    if (!name.trim()) return onClose();
    setBusy(true);
    const failed = await onAdd(name);
    setBusy(false);
    if (failed) return setError(failed);
    setName("");
    setError(null);
    onTyped(false);
    field.current?.focus();
  }

  return (
    <div className="w-48">
      <TextInput
        ref={field}
        autoFocus
        value={name}
        readOnly={busy}
        placeholder={`A skill for ${group.label}`}
        aria-label={`New skill in ${group.label}`}
        aria-invalid={error ? true : undefined}
        maxLength={60}
        onChange={(event) => {
          setName(event.target.value);
          onTyped(event.target.value.trim() !== "");
        }}
        onBlur={() => !name.trim() && !busy && onClose()}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void save();
          }
        }}
      />
      {error && (
        <p role="alert" className="text-note text-danger mt-1">
          {error}
        </p>
      )}
    </div>
  );
}
