"use client";

import { useEffect, type ComponentProps, type ReactNode } from "react";

import { Tip } from "@/components/ui/tip";
import { cn } from "@/lib/cn";

/**
 * What can be done to a table's picked rows (2026-11-11, after Notion's):
 * a small white bar that shows while at least one row is picked, over the
 * table's filter row, so the actions sit right above the rows they act on
 * and the page moves nothing. "N selected" in brand ink first, then one
 * segment per action, a rule between each: a glyph and its word
 * (`SelectionAction`), or a glyph alone with a tooltip for a delete or
 * remove (`iconOnly`), last. No close button: the user found a × beside
 * the actions confusing (it read as one more action). Escape clears the
 * pick, and so does the table's Select All box while any row is picked.
 *
 * The caller places it: `absolute` over the filter row, which takes
 * `SELECTION_ROW`. Up Next's and Documents' resumes.
 */
export function SelectionBar({
  count,
  onClear,
  className,
  children,
}: {
  count: number;
  onClear: () => void;
  className?: string;
  children: ReactNode;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      // A dialog or a menu takes Escape first.
      if (event.key === "Escape" && !event.defaultPrevented) onClear();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClear]);

  return (
    <div
      role="toolbar"
      aria-label={`${count} selected`}
      className={cn(
        "bg-panel border-border-surface rounded-control shadow-lift animate-fade divide-border-subtle z-20 flex h-10 items-stretch divide-x overflow-hidden border",
        className,
      )}
    >
      <span className="text-body text-brand flex items-center px-4 whitespace-nowrap tabular-nums">
        {count} selected
      </span>
      {children}
    </div>
  );
}

/** The filter row the bar is laid over: `relative` for the bar, and while
 *  it shows, the row's other controls hidden, so no half-covered dropdown
 *  peeks out beside it. They come back with the pick's end. */
export const SELECTION_ROW = "relative [&:has(>[role=toolbar])>*:not([role=toolbar])]:invisible";

/**
 * One action in the bar, the whole segment its target: a glyph and its
 * word, or with `iconOnly` the glyph alone in a square segment, named by
 * its tooltip (Delete, Remove). Below `@lg` of the row the bar sits in (a
 * phone's) every word folds away and stays as the name and tooltip, so the
 * bar fits a 343px row.
 */
export function SelectionAction({
  label,
  icon,
  iconOnly = false,
  danger = false,
  className,
  ...button
}: { label: string; icon: ReactNode; iconOnly?: boolean; danger?: boolean } & Omit<
  ComponentProps<"button">,
  "children"
>) {
  return (
    <Tip label={label}>
      <button
        type="button"
        aria-label={label}
        className={cn(
          "text-body text-ink hover:bg-hover focus-visible:ring-brand-ring flex items-center justify-center gap-2 whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
          iconOnly ? "w-10" : "min-w-10 px-2 @lg:px-4",
          danger && "hover:text-danger",
          className,
        )}
        {...button}
      >
        {icon}
        {!iconOnly && <span className="hidden @lg:inline">{label}</span>}
      </button>
    </Tip>
  );
}

/** A row's select box. Its clicks stop here: a row's own click opens it
 *  (components/clickable-row.tsx), and a pick should not. Up Next's and
 *  Documents' tables. */
export function PickBox({ children }: { children: ReactNode }) {
  return (
    <span className="flex shrink-0 items-center" onClick={(event) => event.stopPropagation()}>
      {children}
    </span>
  );
}
