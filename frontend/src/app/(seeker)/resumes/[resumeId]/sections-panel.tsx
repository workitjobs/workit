"use client";

import { CaretDownIcon, DotsSixVerticalIcon } from "@phosphor-icons/react/ssr";
import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { PencilIcon, PlusIcon, TrashIcon, UserIcon } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { Tip } from "@/components/ui/tip";
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
 * mouse. A section's order is a page setting, and an entry's, bullet's or
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
// A drop line above or below a row while one is dragged over it
const LINE_ABOVE = "before:bg-brand before:absolute before:inset-x-0 before:-top-px before:h-0.5";
const LINE_BELOW = "after:bg-brand after:absolute after:inset-x-0 after:-bottom-px after:h-0.5";
const HINT = "Drag to move, or use the arrow keys";

function Handle({
  label,
  onDragStart,
  onDragEnd,
  onKeyDown,
  data,
}: {
  label: string;
  onDragStart: (event: DragEvent<HTMLButtonElement>) => void;
  onDragEnd: () => void;
  onKeyDown: (event: KeyboardEvent) => void;
  /** Finds the handle again after a move remounts its row. */
  data?: string;
}) {
  return (
    <Tip label={HINT}>
      <button
        type="button"
        draggable
        aria-label={`Move ${label}`}
        data-outline-handle={data}
        className="text-ink-meta hover:text-ink focus-visible:ring-brand-ring flex h-7 w-5 shrink-0 cursor-grab items-center justify-center rounded-xs focus-visible:ring-2 focus-visible:outline-none active:cursor-grabbing"
        onDragStart={(event) => {
          event.stopPropagation();
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", label);
          const shown = event.currentTarget.closest("li");
          if (shown) event.dataTransfer.setDragImage(shown, 12, 12);
          onDragStart(event);
        }}
        onDragEnd={onDragEnd}
        onKeyDown={onKeyDown}
      >
        <DotsSixVerticalIcon aria-hidden weight="bold" className="size-4" />
      </button>
    </Tip>
  );
}

/** One list's rows, in order: a drop line while one is dragged over it.
 *  Each list keeps its own drag, so a bullet dropped on a section does
 *  nothing. */
function SortableList<T>({
  items,
  idOf,
  labelOf,
  onMove,
  row,
  className,
}: {
  items: T[];
  idOf: (item: T) => string;
  labelOf: (item: T) => string;
  onMove: (from: number, to: number) => void;
  /** A row, given its handle. */
  row: (item: T, handle: ReactNode) => ReactNode;
  className?: string;
}) {
  const [dragged, setDragged] = useState<number | null>(null);
  // Where the row would land: before the row at this index
  const [gap, setGap] = useState<number | null>(null);

  const over = (event: DragEvent<HTMLLIElement>, at: number) => {
    if (dragged === null) return;
    event.preventDefault();
    event.stopPropagation();
    const box = event.currentTarget.getBoundingClientRect();
    setGap(event.clientY < box.top + box.height / 2 ? at : at + 1);
  };
  const drop = (event: DragEvent) => {
    if (dragged === null || gap === null) return;
    event.preventDefault();
    event.stopPropagation();
    // Taking the row out moves every later row up one
    const to = gap > dragged ? gap - 1 : gap;
    if (to !== dragged) onMove(dragged, to);
    setDragged(null);
    setGap(null);
  };
  const keys = (event: KeyboardEvent, at: number) => {
    const to = event.key === "ArrowUp" ? at - 1 : event.key === "ArrowDown" ? at + 1 : null;
    if (to === null) return;
    event.preventDefault();
    if (to >= 0 && to < items.length) onMove(at, to);
  };

  return (
    <ul role="list" className={cn("flex flex-col", className)} onDrop={drop}>
      {items.map((item, at) => (
        <li
          key={idOf(item)}
          onDragOver={(event) => over(event, at)}
          onDrop={drop}
          className={cn(
            "relative",
            dragged === at && "opacity-50",
            gap === at && LINE_ABOVE,
            gap === at + 1 && at === items.length - 1 && LINE_BELOW,
          )}
        >
          {row(
            item,
            <Handle
              label={labelOf(item)}
              onDragStart={() => setDragged(at)}
              onDragEnd={() => {
                setDragged(null);
                setGap(null);
              }}
              onKeyDown={(event) => keys(event, at)}
            />,
          )}
        </li>
      ))}
    </ul>
  );
}

function Fold({ open, label, onToggle }: { open: boolean; label: string; onToggle: () => void }) {
  return (
    <Tip label={`${open ? "Close" : "Open"} ${label}`}>
      <button
        type="button"
        aria-expanded={open}
        aria-label={`${open ? "Close" : "Open"} ${label}`}
        className="text-ink-meta hover:bg-ink/5 hover:text-ink focus-visible:ring-brand-ring flex size-7 shrink-0 items-center justify-center rounded-full focus-visible:ring-2 focus-visible:outline-none"
        onClick={onToggle}
      >
        <CaretDownIcon
          aria-hidden
          className={cn("size-4 transition-transform duration-150", open && "rotate-180")}
        />
      </button>
    </Tip>
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
    <IconButton label={label} tooltip={tooltip} className="size-7" onClick={onClick}>
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
}: {
  handle: ReactNode;
  name: string;
  detail?: string | null;
  actions?: ReactNode;
  fold?: ReactNode;
  onPress: () => void;
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
      {actions && <div className={ACTIONS}>{actions}</div>}
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
        document
          .querySelector<HTMLElement>(`[data-outline-handle="${CSS.escape(refocus)}"]`)
          ?.focus(),
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
  const sections = printedSections(bank, choices, order);
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
        <section ref={headerRow} className="scroll-mt-2 pb-1.5">
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
          const moved = moveItem(sections, from, to).map((section) => section.id);
          onOrder([
            ...moved,
            ...order.filter((id) => !moved.includes(id) && !id.startsWith("custom:")),
          ]);
        }}
        row={(section, handle) => {
          const open = opened.has(section.id);
          const isSkills = section.id === "skills";
          return (
            <section className="py-1.5">
              <div className={LINE}>
                {handle}
                <button type="button" className={SECTION_NAME} onClick={() => toggle(section.id)}>
                  {section.label}
                </button>
                <div className={ACTIONS}>
                  {!isSkills && section.addable && onAddEntry && (
                    <Add
                      label={`Add ${section.noun}`}
                      onClick={() => {
                        // The new entry shows in the open section
                        if (!open) toggle(section.id);
                        onAddEntry(section.id, document.activeElement as HTMLElement);
                      }}
                    />
                  )}
                  <Remove
                    name={section.label}
                    onRemove={() =>
                      isSkills
                        ? removeSkills(skills.flatMap((group) => group.skills.map((s) => s.id)))
                        : removeEntries(section.entries.map((entry) => entry.id))
                    }
                  />
                </div>
                <Fold open={open} label={section.label} onToggle={() => toggle(section.id)} />
              </div>
              {open && isSkills && (
                <SkillsOutline
                  groups={skills}
                  opened={opened}
                  toggle={toggle}
                  reveal={(id) => !opened.has(id) && toggle(id)}
                  onArrange={(groups) => onApply(arrangeSkills(bank, choices, groups))}
                  onRemove={removeSkills}
                  onAddSkill={onAddSkill}
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
