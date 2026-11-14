"use client";

import Link from "next/link";
import { useState } from "react";

import { isPlainClick, useShallowPush } from "@/components/shallow-routing";
import { cn } from "@/lib/cn";

export type TabLink = { value: string; label: string; href: string };

/** A tab's look, open or not, shared by the link tabs and the button tabs. */
function tabClasses(open: boolean, ruled: boolean) {
  return cn(
    "text-subtitle hit-area focus-visible:ring-brand-ring relative rounded-xs py-2 whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none",
    ruled && "-mb-px",
    "before:absolute before:inset-x-0 before:bottom-0 before:h-[3px] before:rounded-full before:transition-colors before:duration-150",
    open
      ? "text-brand before:bg-brand font-semibold"
      : "text-ink-meta hover:text-ink hover:before:bg-border-strong font-medium before:bg-transparent",
  );
}

/** The label at the semibold label's width, held by an invisible copy, so
 *  a tab never shifts the row when it opens. */
function TabLabel({ label }: { label: string }) {
  return (
    <span className="grid">
      <span aria-hidden="true" className="invisible col-start-1 row-start-1 font-semibold">
        {label}
      </span>
      <span className="col-start-1 row-start-1 text-center">{label}</span>
    </span>
  );
}

/**
 * `TabLinks`' tabs as buttons, for content one screen switches between and
 * the URL need not hold (the resume editor's side panel, Sections and
 * Format, KAN-586): a `tablist` whose open tab is `aria-selected`, with the
 * arrow keys moving between them. The same look as `TabLinks`.
 */
export function TabButtons<V extends string>({
  label,
  options,
  value,
  onChange,
  ruled = false,
  className,
}: {
  /** Names the tabs for a screen reader. */
  label: string;
  options: { value: V; label: string }[];
  value: V;
  onChange: (value: V) => void;
  ruled?: boolean;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn("flex items-center gap-7", ruled && "border-border-subtle border-b", className)}
      onKeyDown={(event) => {
        const at = options.findIndex((o) => o.value === value);
        const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
        if (!step) return;
        event.preventDefault();
        const next = options[(at + step + options.length) % options.length];
        onChange(next.value);
        requestAnimationFrame(() =>
          event.currentTarget.querySelector<HTMLElement>(`[data-tab="${next.value}"]`)?.focus(),
        );
      }}
    >
      {options.map((option) => {
        const open = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            data-tab={option.value}
            aria-selected={open}
            tabIndex={open ? 0 : -1}
            onClick={() => onChange(option.value)}
            className={tabClasses(open, ruled)}
          >
            <TabLabel label={option.label} />
          </button>
        );
      })}
    </div>
  );
}

/**
 * Tabs that move between different content on one subject (KAN-766): a
 * job's Overview and Company, an application's own page and its job
 * description, Documents' Resumes and Cover Letters. Each is a link, kept
 * in the URL, so a tab can be linked to and survives a reload.
 *
 * TABS OR A SWITCHER. A switcher (`ui/segmented-control.tsx`) changes how
 * the same content looks, or one setting: List or Grid, Week or Month, per
 * hour or per year. Tabs move between different content. Material Design
 * and Nielsen Norman Group draw the line the same way; the job page and the
 * application page used the switcher for both until KAN-766, which read as
 * a setting of one view rather than a way to another.
 *
 * Drawn as text with a brand underline on the open tab, not a pill: the
 * pill is the switcher's, so the two never look alike. The underline is
 * `before:`, since `hit-area` (the 24px, and on touch 44px, target) takes
 * `::after`.
 *
 * DISTINCT BESIDE BUTTONS (2026-11-10). A tab is 16px (`text-subtitle`):
 * the open one semibold in brand over a 3px brand underline, the others
 * medium in `ink-meta`, ink with a grey underline under the pointer. At
 * 13px in ink with a 2px underline they read as small print beside the
 * bar's 36px buttons, which the user found overshadowed them. Brand is the
 * colour of what is on or picked (frontend/docs/design.md, icon colour
 * rule). Each label holds the semibold label's width in an invisible copy
 * under it, so a tab never shifts the row when it opens.
 *
 * `shallow` moves the query in place (components/shallow-routing.tsx), for
 * panes the page already drew, as `SegmentedLinks` does; without it the
 * tab is a link to another route that reads its own data. The tab clicked
 * shows as open at once, ahead of the URL.
 */
export function TabLinks({
  label,
  options,
  value,
  shallow = false,
  ruled = false,
  className,
}: {
  /** Names the tabs for a screen reader: "Job Tabs". */
  label: string;
  options: TabLink[];
  value: string;
  shallow?: boolean;
  /** A rule under the row, the open tab's underline on it: for a row of
   *  tabs heading a page (Documents), not tabs inside a bar. */
  ruled?: boolean;
  className?: string;
}) {
  const push = useShallowPush();
  // The tab clicked, ahead of the URL catching up; dropped once `value`
  // changes, which is the navigation confirming it.
  const [pending, setPending] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(value);
  if (confirmed !== value) {
    setConfirmed(value);
    setPending(null);
  }
  const shown = pending ?? value;

  return (
    <nav
      aria-label={label}
      className={cn("flex items-center gap-7", ruled && "border-border-subtle border-b", className)}
    >
      {options.map((option) => {
        const open = option.value === shown;
        return (
          <Link
            key={option.value}
            href={option.href}
            aria-current={option.value === value ? "page" : undefined}
            prefetch={shallow ? false : undefined}
            onClick={(event) => {
              if (!isPlainClick(event)) return;
              setPending(option.value);
              if (shallow) {
                event.preventDefault();
                push(option.href);
              }
            }}
            className={tabClasses(open, ruled)}
          >
            <TabLabel label={option.label} />
          </Link>
        );
      })}
    </nav>
  );
}
