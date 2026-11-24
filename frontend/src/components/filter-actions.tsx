"use client";

import type { Ref } from "react";

import { CloseIcon, FilterIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

/**
 * A filter row's last two controls, the same on every page that has one
 * (2026-11-10, the user's call, after Notion's table toolbar): the Jobs page
 * and the Tracker, which drew them two ways until then.
 *
 * - **Clear** (`ClearFiltersButton`), every pick and the search off in one
 *   press, shown only while there is one: a text button with a cross, since
 *   it acts on what is shown (frontend/docs/design.md, which button look).
 * - **All Filters** (`AllFiltersButton`), the panel with every filter: a
 *   round icon button on the grey ground (`soft`), three lines of falling
 *   length (`FilterIcon`), named by its tooltip and, while anything is
 *   picked, a brand badge on its corner that counts it ("All Filters, 3 on"
 *   to a screen reader), since the facets that step out of a narrow row
 *   show nowhere else. It was in words on the Tracker for a while.
 *
 * Each page keeps their room in its row whether or not Clear shows, so a
 * pick never pushes a facet out (the rows' notes say how wide).
 */
export function AllFiltersButton({
  ref,
  count,
  onClick,
  className,
}: {
  ref?: Ref<HTMLButtonElement>;
  /** What is picked: facets on the Jobs page, values on the Tracker. */
  count: number;
  onClick: () => void;
  className?: string;
}) {
  return (
    <IconButton
      ref={ref}
      label={count > 0 ? `All Filters, ${count} on` : "All Filters"}
      tooltip="All Filters"
      variant="soft"
      onClick={onClick}
      className={cn("relative size-9 shrink-0", className)}
    >
      <FilterIcon className="size-4" />
      {count > 0 && (
        <span
          aria-hidden="true"
          className="bg-brand text-on-brand text-meta absolute -top-1.5 -right-1.5 flex h-4.5 min-w-4.5 items-center justify-center rounded-full px-1 font-semibold tabular-nums"
        >
          {count}
        </span>
      )}
    </IconButton>
  );
}

/** Clear: see `AllFiltersButton`. The caller hands focus on to All
 *  Filters, since the button leaves with the last pick. */
export function ClearFiltersButton({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <Button variant="section" onClick={onClick} className={className}>
      <CloseIcon className="size-4" />
      Clear
    </Button>
  );
}
