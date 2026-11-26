"use client";

import type { ComponentType, ReactNode } from "react";

import { Dialog, DialogContent, DialogTitle } from "@/components/shadcn/dialog";
import { Skeleton } from "@/components/shadcn/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/**
 * The All Filters panel (2026-11-11), one frame for every page that has
 * one: the Jobs page's (jobs/all-filters.tsx, KAN-823), the Tracker's
 * (applications/field-filters.tsx), Auto Apply's Up Next
 * (auto-apply/queue-filters.tsx) and Documents' resumes
 * (resumes/resume-filters.tsx), opened by `AllFiltersButton`
 * (components/filter-actions.tsx). The Jobs page drew a copy of its own
 * until KAN-823.
 *
 * A dialog titled All Filters over a scrolling column of `FilterSection`s
 * and a foot with Clear All and "Show 12 Applications". The picks are a
 * draft until Show, which counts it; closing drops it. `children` mounts
 * only while the dialog is open, so the caller's draft (its state) starts
 * from the table's picks at each opening. A panel whose options load
 * (the Jobs page's places and roles) shows `AllFiltersSkeleton` meanwhile.
 */
export function AllFiltersDialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[min(44rem,calc(100dvh-2rem))] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <div className="border-border-subtle flex items-center border-b px-5 py-3.5 pr-12">
          <DialogTitle>All Filters</DialogTitle>
        </div>
        {open && children}
      </DialogContent>
    </Dialog>
  );
}

/** The panel's sections, then its foot: Clear All on the left, Show on the
 *  right with the draft's count ("Show 4 Jobs"). */
export function AllFiltersBody({
  children,
  onClear,
  onShow,
  showLabel,
}: {
  children: ReactNode;
  onClear: () => void;
  onShow: () => void;
  showLabel: string;
}) {
  return (
    <>
      {/* overscroll-none: a fling past the end stops here instead of
          scrolling the page behind. */}
      <div data-panel-scroll className="min-h-0 flex-1 overflow-y-auto overscroll-none px-5">
        {children}
      </div>
      <div className="border-border-subtle flex items-center justify-between gap-3 border-t px-5 py-3">
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear All
        </Button>
        <Button size="sm" onClick={onShow}>
          {showLabel}
        </Button>
      </div>
    </>
  );
}

/** The panel's body while its options load (KAN-823; it was the line
 *  "Loading the filters…"): `sections` sections as bars, each a glyph and
 *  name over a row of chips, then the foot's two buttons, at the heights of
 *  what replaces them. The dialog's title stays real. */
export function AllFiltersSkeleton({ sections }: { sections: number }) {
  return (
    <div role="status" className="flex min-h-0 flex-1 flex-col">
      <span className="sr-only">Loading the filters</span>
      <div aria-hidden="true" className="min-h-0 flex-1 overflow-hidden px-5">
        {Array.from({ length: sections }, (_, i) => (
          <div key={i} className={cn("py-4", i > 0 && "border-border-subtle border-t")}>
            <div className="mb-2.5 flex h-5 items-center gap-2">
              <Skeleton className="size-4 shrink-0" />
              <Skeleton className="h-3.5 w-28" />
            </div>
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-9 w-24 rounded-full" />
              <Skeleton className="h-9 w-28 rounded-full" />
              <Skeleton className="h-9 w-20 rounded-full" />
            </div>
          </div>
        ))}
      </div>
      <div
        aria-hidden="true"
        className="border-border-subtle flex items-center justify-between gap-3 border-t px-5 py-3"
      >
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-28" />
      </div>
    </div>
  );
}

/** One field's section: its glyph and name over its options (chips or a
 *  search picker), ruled from the one before. */
export function FilterSection({
  Icon,
  label,
  first = false,
  children,
}: {
  Icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  label: string;
  first?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={cn("py-4", !first && "border-border-subtle border-t")}>
      <h3 className="text-body text-ink mb-2.5 flex items-center gap-2 font-semibold">
        <Icon aria-hidden className="text-ink-meta size-4 shrink-0" />
        {label}
      </h3>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </section>
  );
}
