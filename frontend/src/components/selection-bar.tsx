"use client";

import { useEffect, type ComponentProps, type ReactNode } from "react";

import { CloseIcon } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

/**
 * What can be done to a table's picked rows (2026-11-11, after Notion's):
 * a small white bar that shows while at least one row is picked, over the
 * table's filter row, so the actions sit right above the rows they act on
 * and the page moves nothing. The count in brand ink first, then one
 * segment per action, a rule between each, then Clear. Escape clears the
 * pick too. The table's own select boxes pick (`PickBox` in each row,
 * Select All in its first heading).
 *
 * The caller places it: `absolute` over the filter row, which is
 * `relative`. Its actions are `SelectionAction`s.
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
        "bg-panel border-border-subtle rounded-control shadow-lift animate-fade divide-border-subtle z-20 flex h-10 items-center divide-x overflow-hidden border",
        className,
      )}
    >
      <span className="text-note text-brand px-3 font-medium whitespace-nowrap tabular-nums">
        {count} selected
      </span>
      {children}
      <span className="flex h-full items-center px-1">
        <IconButton label="Clear selection" tooltip="Clear (Esc)" onClick={onClear}>
          <CloseIcon className="size-4" />
        </IconButton>
      </span>
    </div>
  );
}

/** One action in the bar: its glyph and word, the whole segment the
 *  target. Below `@lg` of the row the bar sits in (a phone's), the word
 *  folds away and stays as the button's name and tooltip, so the bar fits
 *  a 343px row. */
export function SelectionAction({
  label,
  icon,
  danger = false,
  className,
  ...button
}: { label: string; icon: ReactNode; danger?: boolean } & Omit<
  ComponentProps<"button">,
  "children"
>) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "text-note text-ink hover:bg-hover focus-visible:ring-brand-ring flex h-full items-center gap-1.5 px-3 font-medium whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4",
        danger && "hover:text-danger",
        className,
      )}
      {...button}
    >
      {icon}
      <span className="hidden @lg:inline">{label}</span>
    </button>
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
