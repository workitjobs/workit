"use client";

import Link from "next/link";
import { useState } from "react";

import { isPlainClick, useShallowPush } from "@/components/shallow-routing";
import { cn } from "@/lib/cn";

export type TabLink = { value: string; label: string; href: string };

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
      className={cn("flex items-center gap-6", ruled && "border-border-subtle border-b", className)}
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
            className={cn(
              "text-label hit-area focus-visible:ring-brand-ring relative rounded-xs py-2 font-medium whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none",
              ruled && "-mb-px",
              "before:absolute before:inset-x-0 before:bottom-0 before:h-0.5 before:rounded-full before:transition-colors before:duration-150",
              open
                ? "text-ink before:bg-brand"
                : "text-ink-meta hover:text-ink before:bg-transparent",
            )}
          >
            {option.label}
          </Link>
        );
      })}
    </nav>
  );
}
