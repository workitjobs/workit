"use client";

import { DotsSixVerticalIcon } from "@phosphor-icons/react/ssr";
import { useState, type DragEvent, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * Rows the student drags into order, or moves with the arrow keys: the
 * resume editor's Sections panel (KAN-586: sections, entries, skill groups
 * and skills) and the Experiences page's Skills dialog (KAN-816: skill
 * groups, and each group's skills as chips). One handle and one drop line,
 * so a drag looks and acts the same on both.
 *
 * Only a handle is `draggable`, so a press on the rest of a row still does
 * what the row does, and a handle is a button: its arrow keys move the row,
 * for a student with no mouse. A row that remounts after a move (a skill
 * into another group) finds its handle again by `data`, `data-handle`.
 */

// A drop line above or below a row while one is dragged over it
export const LINE_ABOVE =
  "before:bg-brand before:absolute before:inset-x-0 before:-top-px before:h-0.5";
export const LINE_BELOW =
  "after:bg-brand after:absolute after:inset-x-0 after:-bottom-px after:h-0.5";
// The same before or after a chip in a wrapped row of chips
export const LINE_BEFORE =
  "before:bg-brand before:absolute before:inset-y-0 before:-left-1.5 before:w-0.5";
export const LINE_AFTER =
  "after:bg-brand after:absolute after:inset-y-0 after:-right-1.5 after:w-0.5";

export function Handle({
  label,
  onDragStart,
  onDragEnd,
  onKeyDown,
  data,
  className,
  children,
}: {
  label: string;
  onDragStart: (event: DragEvent<HTMLButtonElement>) => void;
  onDragEnd: () => void;
  onKeyDown: (event: KeyboardEvent) => void;
  /** Finds the handle again after a move remounts its row. */
  data?: string;
  /** In place of the dots' box: a chip's name is its own handle. */
  className?: string;
  /** What the handle shows: the dots, unless a chip shows its name. */
  children?: ReactNode;
}) {
  return (
    <button
      type="button"
      draggable
      aria-label={`Move ${label}`}
      data-handle={data}
      className={cn(
        "focus-visible:ring-brand-ring cursor-grab focus-visible:ring-2 focus-visible:outline-none active:cursor-grabbing",
        className ??
          "text-ink-meta hover:text-ink flex h-7 w-5 shrink-0 items-center justify-center rounded-xs",
      )}
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
      {children ?? <DotsSixVerticalIcon aria-hidden weight="bold" className="size-4" />}
    </button>
  );
}

/** One list's rows, in order: a drop line while one is dragged over it.
 *  Each list keeps its own drag, so a bullet dropped on a section does
 *  nothing. */
export function SortableList<T>({
  items,
  idOf,
  labelOf,
  dataOf,
  onMove,
  row,
  className,
}: {
  items: T[];
  idOf: (item: T) => string;
  labelOf: (item: T) => string;
  /** The handle's `data`, to find it again after a move. */
  dataOf?: (item: T) => string;
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
              data={dataOf?.(item)}
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
