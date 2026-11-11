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

import { UserIcon } from "@/components/icons";
import { Tip } from "@/components/ui/tip";
import type { Bank } from "@/lib/bank-actions";
import type { Choices, ChoicesUpdate } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

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

/** An entry or a skill group: its name over a muted line, both a press
 *  that folds it. */
function ItemRow({
  handle,
  name,
  detail,
  fold,
  onToggle,
}: {
  handle: ReactNode;
  name: string;
  detail?: string | null;
  fold: ReactNode;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center gap-1 py-0.5">
      {handle}
      <button
        type="button"
        className="group/row focus-visible:outline-brand min-w-0 flex-1 text-left focus-visible:outline-2"
        onClick={onToggle}
      >
        <span className={ITEM_NAME}>{name}</span>
        {detail && <span className="text-note text-ink-meta block truncate">{detail}</span>}
      </button>
      {fold}
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
}: {
  groups: PrintedSkillGroup[];
  opened: Set<string>;
  toggle: (id: string) => void;
  /** Opens a row, leaving it open if it is. */
  reveal: (id: string) => void;
  onArrange: (groups: PrintedSkillGroup[]) => void;
}) {
  const [dragged, setDragged] = useState<Spot | null>(null);
  // Where the skill would land: before the skill at this index of its group
  const [gap, setGap] = useState<Spot | null>(null);
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
              onToggle={() => toggle(id)}
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
                      "relative flex items-center gap-1",
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
                  </li>
                ))}
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

  const entryRow = (entry: PrintedEntry, handle: ReactNode) => {
    const open = opened.has(entry.id);
    return (
      <div>
        <ItemRow
          handle={handle}
          name={entry.title}
          detail={entry.detail}
          onToggle={() => toggle(entry.id)}
          fold={
            entry.bullets.length > 1 && (
              <Fold open={open} label={entry.title} onToggle={() => toggle(entry.id)} />
            )
          }
        />
        {open && (
          <SortableList
            items={entry.bullets}
            idOf={(bullet) => bullet.id}
            labelOf={(bullet) => bullet.text.slice(0, 40)}
            className={cn(NEST, "gap-0.5 pb-1")}
            onMove={(from, to) =>
              onApply({
                bullets: moveItem(entry.bullets, from, to).map(({ id }, position) => ({
                  bullet_id: id,
                  position,
                })),
              })
            }
            row={(bullet, handle) => (
              <div className="flex items-center gap-1">
                {handle}
                <span className={cn(LEAF, "line-clamp-2")}>{bullet.text}</span>
              </div>
            )}
          />
        )}
      </div>
    );
  };

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
          {headerOpen && <div className="pt-2 pb-2 pl-6">{header}</div>}
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
          const filled = isSkills ? skills.length > 0 : section.entries.length > 0;
          return (
            <section className="py-1.5">
              <div className="flex items-center gap-1">
                {handle}
                <button type="button" className={SECTION_NAME} onClick={() => toggle(section.id)}>
                  {section.label}
                </button>
                {filled && (
                  <Fold open={open} label={section.label} onToggle={() => toggle(section.id)} />
                )}
              </div>
              {open && isSkills && (
                <SkillsOutline
                  groups={skills}
                  opened={opened}
                  toggle={toggle}
                  reveal={(id) => !opened.has(id) && toggle(id)}
                  onArrange={(groups) => onApply(arrangeSkills(bank, choices, groups))}
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
