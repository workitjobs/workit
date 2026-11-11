"use client";

import { useState, type ComponentType, type ReactNode } from "react";

import { ChevronDownIcon } from "@/components/icons";
import { TableCell, TableRow } from "@/components/shadcn/table";
import { cn } from "@/lib/cn";

/**
 * A group's heading row in a page table, the one look every grouped table
 * draws (2026-11-11): Auto Apply's Up Next (auto-apply/queue-table.tsx),
 * the Tracker's list (applications/list.tsx) and Documents' resumes
 * (resumes/built-resumes.tsx), each grouped by Table Settings' Group By
 * (components/table-settings.tsx). Each table drew its own copy until then.
 *
 * A quiet band (2026-11-10): a fold (the chevron turns while it is shut),
 * an optional glyph in its colour (a stage's), the name in ink and its
 * count, centred on the row's light band, with the group's own action at
 * the right (Remove All on Posting Closed). A pill around the name was as
 * loud as the rows it heads, and heavier padding on top sat the words on
 * the band's floor.
 *
 * The cell spans every column (`colSpan`), so the fold and the action are
 * sticky inside it: a cell that wide scrolls away with the rest, and they
 * stay at the edges while the table scrolls sideways.
 */
export function GroupHeadingRow({
  colSpan,
  label,
  count,
  open,
  onToggle,
  Icon,
  iconClassName,
  action,
}: {
  colSpan: number;
  label: string;
  count: number;
  open: boolean;
  onToggle: () => void;
  Icon?: ComponentType<{ className?: string }>;
  iconClassName?: string;
  action?: ReactNode;
}) {
  return (
    <TableRow className="hover:bg-transparent">
      <TableCell colSpan={colSpan} className="px-4 py-2">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={open}
            className="group/fold focus-visible:ring-brand-ring sticky left-4 flex items-center gap-2 rounded-xs focus-visible:ring-2 focus-visible:outline-none"
          >
            <ChevronDownIcon
              className={cn(
                // Ink under the pointer: the fold had no hover.
                "text-ink-meta group-hover/fold:text-ink size-3.5 transition-[transform,color] duration-150",
                !open && "-rotate-90",
              )}
            />
            {Icon && <Icon className={cn("size-4 shrink-0", iconClassName)} />}
            <span className="text-label text-ink font-semibold">{label}</span>
            <span className="text-note text-ink-meta tabular-nums">{count}</span>
          </button>
          {action && <span className="sticky right-4">{action}</span>}
        </div>
      </TableCell>
    </TableRow>
  );
}

/** Which groups are folded shut, by key, and the toggle for one. Every
 *  group starts open; the folds last while the page is open. */
export function useFolds() {
  const [folded, setFolded] = useState<ReadonlySet<string>>(new Set());
  const toggle = (key: string) =>
    setFolded((now) => {
      const next = new Set(now);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  return [folded, toggle] as const;
}
