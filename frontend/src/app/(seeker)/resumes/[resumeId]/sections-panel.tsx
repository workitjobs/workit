"use client";

import { CaretDownIcon } from "@phosphor-icons/react/ssr";
import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { PencilIcon, PlusIcon, TrashIcon, UserIcon } from "@/components/icons";
import { Handle, LINE_ABOVE, LINE_BELOW, SortableList } from "@/components/sortable-list";
import { IconButton } from "@/components/ui/icon-button";
import type { Bank } from "@/lib/bank-actions";
import type { Choices, ChoicesUpdate } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { TextInput } from "@/components/ui/text-field";

import {
  arrangeSkills,
  moveItem,
  moveSkill,
  printedSections,
  printedSkills,
  sectionOrderAfter,
  type PrintedEntry,
  type PrintedSkillGroup,
} from "./model";

/**
 * The resume as an outline (KAN-435, KAN-586), top to bottom as it prints:
 * the Header, then the sections, each folding to its entries and each entry
 * to its bullets, and Technical Skills folding to its groups and each group
 * to its skills. It is the only way to move a section, a skill group or a
 * skill. The bar's Move Up and Move Down (`MoveButtons` in the editor) move
 * the open entry or bullet one step, and this outline follows them at once,
 * since both read the choices. A phone keeps its own buttons, since a drag
 * there fights the scroll.
 *
 * **Three levels, three looks**: a section's name is the label size in
 * semibold; an entry, a skill group and the Header are a note in medium;
 * a bullet or a skill is a muted note. Each level below a section sits on a
 * guide line one step in, with its handle at that step, so what holds what
 * reads at a glance. Every row that opens has the same chevron at its right
 * end. Until KAN-586 an entry was as bold as its section, beside it at the
 * same indent, and Technical Skills was a row with nothing under it.
 *
 * **The Header is the first row** and never moves: it opens the header's
 * fields (`HeaderPanel`, KAN-436), and a click on the header's line on the
 * page opens it here (`headerOpen`). It was a side panel of its own for a
 * day, beside this one.
 *
 * **A skill moves within its group, to another group, or with its whole
 * group** (KAN-586). A move to another group is this resume's alone (the
 * choice's `group`), never the bank's, so the Experiences page and every
 * other resume keep their groups. A skill dropped on a closed group goes to
 * its end; its arrow keys step past a group's edge into the next one.
 *
 * Only a handle is `draggable`, so a press on a row still folds it, and a
 * handle is a button: its arrow keys move the row, for a student with no
 * mouse (`components/sortable-list.tsx`, shared with the Experiences page's
 * Skills dialog since KAN-816). A section's order is a page setting, and an entry's, bullet's or
 * skill's a choice, so each saves and renders as any edit does, and Undo
 * takes it back. It orders what prints: what shows is the Experiences
 * picker's.
 */

// One step in, with a guide line: an entry under its section, a bullet
// under its entry, a skill under its group
const NEST = "border-border-subtle ml-2.5 border-l pl-1.5";
const SECTION_NAME =
  "text-label text-ink hover:text-brand focus-visible:outline-brand min-w-0 flex-1 truncate py-0.5 text-left font-semibold transition-colors duration-150 focus-visible:outline-2";
const ITEM_NAME =
  "text-note text-ink group-hover/row:text-brand block truncate font-medium transition-colors duration-150";
const LEAF = "text-note text-ink-muted min-w-0 flex-1";

/** A group's fold: `IconButton` at a row's place (KAN-821), with its
 *  tooltip, since the editor's folded tools keep one. It was a 28px button
 *  of its own in grey, which the icon rule keeps for a glyph that only
 *  informs. */
function Fold({ open, label, onToggle }: { open: boolean; label: string; onToggle: () => void }) {
  return (
    <IconButton
      place="row"
      label={`${open ? "Close" : "Open"} ${label}`}
      aria-expanded={open}
      className="shrink-0"
      onClick={onToggle}
    >
      <CaretDownIcon
        aria-hidden
        className={cn("transition-transform duration-150", open && "rotate-180")}
      />
    </IconButton>
  );
}

// A row's actions show while the pointer or the focus is on its line, and
// always on a touch screen, which has no hover
const LINE = "group/line flex items-center gap-1";
const ACTIONS =
  "flex shrink-0 items-center opacity-0 transition-opacity duration-150 group-hover/line:opacity-100 group-focus-within/line:opacity-100 [@media(hover:none)]:opacity-100";

/** A row's Edit or Remove: a quiet glyph, named in full for a screen reader
 *  and in short in its tooltip. */
function Action({
  label,
  tooltip,
  onClick,
  children,
}: {
  label: string;
  tooltip: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <IconButton place="row" label={label} tooltip={tooltip} onClick={onClick}>
      {children}
    </IconButton>
  );
}

/** Remove From This Resume: the row and all under it leave this resume only
 *  (a hide, with Undo); the bank keeps them, and Add Experiences puts them
 *  back. */
function Remove({ name, onRemove }: { name: string; onRemove: () => void }) {
  return (
    <Action
      label={`Remove ${name} from this resume`}
      tooltip="Remove From Resume"
      onClick={onRemove}
    >
      <TrashIcon className="size-4" />
    </Action>
  );
}

/** "+" in a row's actions: Add Job on a section, Add Skill on a group. */
function Add({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Action label={label} tooltip={label} onClick={onClick}>
      <PlusIcon className="size-4" />
    </Action>
  );
}

/** An entry or a skill group: its name over a muted line, both one press
 *  (a group folds, an entry opens its form), then its actions and a group's
 *  fold. */
function ItemRow({
  handle,
  name,
  detail,
  actions,
  fold,
  onPress,
  shown = false,
}: {
  handle: ReactNode;
  name: string;
  detail?: string | null;
  actions?: ReactNode;
  fold?: ReactNode;
  onPress: () => void;
  /** Its actions show without a hover: the walkthrough points at them. */
  shown?: boolean;
}) {
  return (
    <div className={cn(LINE, "py-0.5")}>
      {handle}
      <button
        type="button"
        className="group/row focus-visible:outline-brand min-w-0 flex-1 text-left focus-visible:outline-2"
        onClick={onPress}
      >
        <span className={ITEM_NAME}>{name}</span>
        {detail && <span className="text-note text-ink-meta block truncate">{detail}</span>}
      </button>
      {actions && <div className={cn(ACTIONS, shown && "opacity-100")}>{actions}</div>}
      {fold}
    </div>
  );
}

/** A group's Add Skill (its row's +): a field at the group's foot, where
 *  Enter saves the skill into this group on this resume and leaves the field
 *  open for the next; Escape or leaving it empty closes it. */
function AddSkill({
  group,
  onAdd,
  onClose,
}: {
  group: PrintedSkillGroup;
  onAdd: (group: string, name: string) => Promise<string | null>;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const close = () => {
    setName("");
    setError(null);
    onClose();
  };
  const save = async () => {
    const typed = name.trim();
    if (!typed) return close();
    setBusy(true);
    const failed = await onAdd(group.key, typed);
    setBusy(false);
    if (failed) return setError(failed);
    // Ready for the next one
    setName("");
    setError(null);
  };
  return (
    <div className="py-0.5 pl-6">
      <TextInput
        autoFocus
        value={name}
        disabled={busy}
        placeholder={`A skill for ${group.label}`}
        aria-label={`New skill in ${group.label}`}
        aria-invalid={error ? true : undefined}
        maxLength={60}
        onChange={(event) => setName(event.target.value)}
        onBlur={() => !name.trim() && close()}
        onKeyDown={(event) => {
          if (event.key === "Enter") void save();
          if (event.key === "Escape") close();
        }}
      />
      {error && (
        <div role="alert" className="text-note text-danger mt-1">
          {error}
        </div>
      )}
    </div>
  );
}

type Spot = { group: number; at: number };

/** Technical Skills' groups (KAN-586): each group drags as a whole, and a
 *  skill drags within its group or into another. One drag state for every
 *  group, since a skill crosses lists. */
function SkillsOutline({
  groups,
  opened,
  toggle,
  reveal,
  onArrange,
  onRemove,
  onAddSkill,
  shown = false,
}: {
  groups: PrintedSkillGroup[];
  opened: Set<string>;
  toggle: (id: string) => void;
  /** Opens a row, leaving it open if it is. */
  reveal: (id: string) => void;
  onArrange: (groups: PrintedSkillGroup[]) => void;
  /** Takes these skills off this resume. */
  onRemove: (skillIds: string[]) => void;
  /** Saves a new skill into the group on this resume; an error, or null. */
  onAddSkill?: (group: string, name: string) => Promise<string | null>;
  /** The groups' + shows without a hover (the walkthrough's Skills step). */
  shown?: boolean;
}) {
  const [dragged, setDragged] = useState<Spot | null>(null);
  // Where the skill would land: before the skill at this index of its group
  const [gap, setGap] = useState<Spot | null>(null);
  // The group whose Add Skill field is open, by key
  const [adding, setAdding] = useState<string | null>(null);
  const end = () => {
    setDragged(null);
    setGap(null);
  };

  const move = (from: Spot, to: Spot, refocus?: string) => {
    if (from.group === to.group && from.at === to.at) return;
    // A skill moved into a closed group would vanish from the outline with
    // the focus on it: its new group opens
    reveal(`skills:${groups[to.group].key}`);
    onArrange(moveSkill(groups, from, to));
    // The moved row remounts in its new list: give its handle the focus
    // back, so the arrow keys can keep moving it
    if (refocus)
      requestAnimationFrame(() =>
        document.querySelector<HTMLElement>(`[data-handle="${CSS.escape(refocus)}"]`)?.focus(),
      );
  };
  const drop = (event: DragEvent) => {
    if (dragged === null || gap === null) return;
    event.preventDefault();
    event.stopPropagation();
    // Taking the skill out moves every later skill in its group up one
    const at = gap.group === dragged.group && gap.at > dragged.at ? gap.at - 1 : gap.at;
    move(dragged, { group: gap.group, at });
    end();
  };
  const overSkill = (event: DragEvent<HTMLLIElement>, group: number, at: number) => {
    if (dragged === null) return;
    event.preventDefault();
    event.stopPropagation();
    const box = event.currentTarget.getBoundingClientRect();
    setGap({ group, at: event.clientY < box.top + box.height / 2 ? at : at + 1 });
  };
  // Over a group's own row: the skill goes to the group's end
  const overGroup = (event: DragEvent<HTMLDivElement>, group: number) => {
    if (dragged === null) return;
    event.preventDefault();
    event.stopPropagation();
    setGap({ group, at: groups[group].skills.length });
  };
  const keys = (event: KeyboardEvent, from: Spot, id: string) => {
    const size = groups[from.group].skills.length;
    let to: Spot | null = null;
    if (event.key === "ArrowUp") {
      if (from.at > 0) to = { group: from.group, at: from.at - 1 };
      else if (from.group > 0)
        to = { group: from.group - 1, at: groups[from.group - 1].skills.length };
    } else if (event.key === "ArrowDown") {
      if (from.at < size - 1) to = { group: from.group, at: from.at + 1 };
      else if (from.group < groups.length - 1) to = { group: from.group + 1, at: 0 };
    } else return;
    event.preventDefault();
    if (to) move(from, to, id);
  };

  return (
    <SortableList
      items={groups}
      idOf={(group) => `group:${group.key}`}
      labelOf={(group) => group.label}
      className={cn(NEST, "mt-0.5 gap-0.5")}
      onMove={(from, to) => onArrange(moveItem(groups, from, to))}
      row={(group, handle) => {
        const g = groups.indexOf(group);
        const id = `skills:${group.key}`;
        const open = opened.has(id);
        const target = dragged !== null && gap?.group === g;
        return (
          <div
            onDragOver={(event) => overGroup(event, g)}
            onDrop={drop}
            className={cn("rounded-xs", target && !open && "bg-brand-tint ring-brand ring-1")}
          >
            <ItemRow
              handle={handle}
              name={group.label}
              detail={open ? null : group.skills.map((s) => s.name).join(", ")}
              onPress={() => toggle(id)}
              shown={shown}
              actions={
                <>
                  {onAddSkill && (
                    <Add
                      label={`Add a skill to ${group.label}`}
                      onClick={() => {
                        reveal(id);
                        setAdding(group.key);
                      }}
                    />
                  )}
                  <Remove
                    name={`the ${group.label} skills`}
                    onRemove={() => onRemove(group.skills.map((skill) => skill.id))}
                  />
                </>
              }
              fold={<Fold open={open} label={group.label} onToggle={() => toggle(id)} />}
            />
            {open && (
              <ul role="list" className={cn(NEST, "flex flex-col gap-0.5 pb-1")}>
                {group.skills.map((skill, at) => (
                  <li
                    key={skill.id}
                    onDragOver={(event) => overSkill(event, g, at)}
                    onDrop={drop}
                    className={cn(
                      "relative",
                      LINE,
                      dragged?.group === g && dragged.at === at && "opacity-50",
                      target && gap.at === at && LINE_ABOVE,
                      target && gap.at === at + 1 && at === group.skills.length - 1 && LINE_BELOW,
                    )}
                  >
                    <Handle
                      label={skill.name}
                      data={skill.id}
                      onDragStart={() => setDragged({ group: g, at })}
                      onDragEnd={end}
                      onKeyDown={(event) => keys(event, { group: g, at }, skill.id)}
                    />
                    <span className={cn(LEAF, "truncate")}>{skill.name}</span>
                    <div className={ACTIONS}>
                      <Remove name={skill.name} onRemove={() => onRemove([skill.id])} />
                    </div>
                  </li>
                ))}
                {onAddSkill && adding === group.key && (
                  <li>
                    <AddSkill group={group} onAdd={onAddSkill} onClose={() => setAdding(null)} />
                  </li>
                )}
              </ul>
            )}
          </div>
        );
      }}
    />
  );
}

export function SectionsOutline({
  bank,
  choices,
  order,
  onOrder,
  onApply,
  header,
  headerOpen = false,
  onHeaderOpen,
  onEditEntry,
  onAddEntry,
  onAddSkill,
  lit = [],
  reveal = null,
}: {
  bank: Bank;
  choices: Choices;
  /** The sections in print order: a page setting. */
  order: string[];
  onOrder: (order: string[]) => void;
  onApply: (changes: ChoicesUpdate) => void;
  /** The header's fields (`HeaderPanel`), shown under the Header row. */
  header?: ReactNode;
  /** Whether the Header row is open: the editor's, since a click on the
   *  header's line on the page opens it. */
  headerOpen?: boolean;
  onHeaderOpen?: (open: boolean) => void;
  /** Opens an entry's form (`OutlineEntryDialog`), from its Edit. */
  onEditEntry?: (entryId: string, opener: HTMLElement) => void;
  /** Opens a new entry's form for a section, or none where a section takes
   *  no new entry here (a Lines section). */
  onAddEntry?: (sectionId: string, opener: HTMLElement) => void;
  /** Saves a new skill into a group on this resume; an error, or null. */
  onAddSkill?: (group: string, name: string) => Promise<string | null>;
  /** The sections the editor's tour points at (./tour-steps): their Add
   *  shows without a hover, since the tour's card names it. */
  lit?: string[];
  /** A section the walkthrough opens (its chapter's): shown open whenever
   *  it changes, as a press on its name would. */
  reveal?: string | null;
}) {
  const [opened, setOpened] = useState<Set<string>>(() => new Set());
  // Opened from the page's header line, the Header row may be scrolled out
  // of the panel's view: it comes into view as it opens
  const headerRow = useRef<HTMLElement>(null);
  useEffect(() => {
    if (headerOpen) headerRow.current?.scrollIntoView({ block: "nearest" });
  }, [headerOpen]);
  const toggle = (id: string) => {
    const next = new Set(opened);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpened(next);
  };
  // One section open at a time, the Header among them (KAN-586, the user's
  // call): each open section showed its whole list, and three open at once
  // ran the panel to several screens. Opening one closes the other; the
  // Header opening, here or from the page's header line, closes the section
  const [openSection, setOpenSection] = useState<string | null>(null);
  const showSection = (id: string | null) => {
    setOpenSection(id);
    if (id !== null && headerOpen) onHeaderOpen?.(false);
  };
  const toggleSection = (id: string) => showSection(openSection === id ? null : id);
  const [revealed, setRevealed] = useState<string | null>(null);
  if (revealed !== reveal) {
    setRevealed(reveal);
    if (reveal && reveal !== "header") setOpenSection(reveal);
  }
  const [headerWas, setHeaderWas] = useState(headerOpen);
  if (headerWas !== headerOpen) {
    setHeaderWas(headerOpen);
    if (headerOpen) setOpenSection(null);
  }
  // Education, Experience, Projects and Skills are listed empty too, for
  // their Add: an empty resume listed nothing to add to (2026-11-17)
  const sections = printedSections(bank, choices, order, { withEmpty: true });
  // A first skill's field, opened by an empty Skills row's Add, and kept
  // open after the first save so the next can be typed
  const [firstSkill, setFirstSkill] = useState(false);
  const skills = printedSkills(bank, choices);
  // Remove From This Resume: a hide, so Undo takes it back and the bank
  // keeps the item for Add Experiences to put back
  const removeEntries = (ids: string[]) =>
    onApply({ entries: ids.map((entry_id) => ({ entry_id, shown: false })) });
  const removeSkills = (ids: string[]) =>
    onApply({ skills: ids.map((skill_id) => ({ skill_id, shown: false })) });

  // An entry's row opens its form (name, pencil): its bullets, their order
  // on this resume and which of them show are edited there, where the
  // panel's narrow rows cut them at two lines
  const editEntry = (entryId: string) =>
    onEditEntry?.(entryId, document.activeElement as HTMLElement);
  const entryRow = (entry: PrintedEntry, handle: ReactNode) => (
    <ItemRow
      handle={handle}
      name={entry.title}
      detail={entry.detail}
      onPress={() => editEntry(entry.id)}
      actions={
        <>
          {onEditEntry && (
            <Action
              label={`Edit ${entry.title}`}
              tooltip="Edit"
              onClick={() => editEntry(entry.id)}
            >
              <PencilIcon className="size-4" />
            </Action>
          )}
          <Remove name={entry.title} onRemove={() => removeEntries([entry.id])} />
        </>
      }
    />
  );

  return (
    <div className="divide-border-subtle flex flex-col divide-y">
      {header && (
        <section ref={headerRow} data-tour="section-header" className="scroll-mt-2 pb-1.5">
          <div className="flex items-center gap-1">
            <span className="text-ink-meta flex h-7 w-5 shrink-0 items-center justify-center">
              <UserIcon className="size-4" />
            </span>
            <button
              type="button"
              className={SECTION_NAME}
              onClick={() => onHeaderOpen?.(!headerOpen)}
            >
              Header
            </button>
            <Fold open={headerOpen} label="Header" onToggle={() => onHeaderOpen?.(!headerOpen)} />
          </div>
          {headerOpen && <div className="pt-2 pb-2">{header}</div>}
        </section>
      )}
      <SortableList
        items={sections}
        idOf={(section) => section.id}
        labelOf={(section) => section.label}
        className="divide-border-subtle divide-y"
        onMove={(from, to) => {
          // Only the sections that print are here; the rest keep their places
          // after them, so a section the student adds later lands in its usual
          // spot. A custom section that no longer prints leaves the order
          // (KAN-498): it comes back where a new one goes
          onOrder(
            sectionOrderAfter(
              sections.map((section) => section.id),
              order,
              from,
              to,
            ),
          );
        }}
        row={(section, handle) => {
          const open = openSection === section.id;
          const isSkills = section.id === "skills";
          return (
            <section className="py-1.5">
              <div className={LINE} data-tour={`section-${section.id}`}>
                {handle}
                <button
                  type="button"
                  className={SECTION_NAME}
                  onClick={() => toggleSection(section.id)}
                >
                  {section.label}
                </button>
                <div className={cn(ACTIONS, lit.includes(section.id) && "opacity-100")}>
                  {isSkills && section.empty && onAddSkill && (
                    <Add
                      label="Add Skill"
                      onClick={() => {
                        showSection(section.id);
                        setFirstSkill(true);
                      }}
                    />
                  )}
                  {!isSkills && section.addable && onAddEntry && (
                    <Add
                      label={`Add ${section.noun}`}
                      onClick={() => {
                        // The new entry shows in the open section
                        showSection(section.id);
                        onAddEntry(section.id, document.activeElement as HTMLElement);
                      }}
                    />
                  )}
                  {!section.empty && (
                    <Remove
                      name={section.label}
                      onRemove={() =>
                        isSkills
                          ? removeSkills(skills.flatMap((group) => group.skills.map((s) => s.id)))
                          : removeEntries(section.entries.map((entry) => entry.id))
                      }
                    />
                  )}
                </div>
                <Fold
                  open={open}
                  label={section.label}
                  onToggle={() => toggleSection(section.id)}
                />
              </div>
              {open && isSkills && !section.empty && (
                <SkillsOutline
                  groups={skills}
                  opened={opened}
                  toggle={toggle}
                  reveal={(id) => !opened.has(id) && toggle(id)}
                  onArrange={(groups) => onApply(arrangeSkills(bank, choices, groups))}
                  onRemove={removeSkills}
                  onAddSkill={onAddSkill}
                  shown={lit.includes("skills")}
                />
              )}
              {open && isSkills && firstSkill && onAddSkill && (
                <AddSkill
                  group={{ key: "", label: "Technical Skills", skills: [] }}
                  onAdd={onAddSkill}
                  onClose={() => setFirstSkill(false)}
                />
              )}
              {open && !isSkills && section.entries.length > 0 && (
                <SortableList
                  items={section.entries}
                  idOf={(entry) => entry.id}
                  labelOf={(entry) => entry.title}
                  className={cn(NEST, "mt-0.5 gap-0.5")}
                  onMove={(from, to) =>
                    onApply({
                      entries: moveItem(section.entries, from, to).map(({ id }, position) => ({
                        entry_id: id,
                        position,
                      })),
                    })
                  }
                  row={entryRow}
                />
              )}
            </section>
          );
        }}
      />
    </div>
  );
}
