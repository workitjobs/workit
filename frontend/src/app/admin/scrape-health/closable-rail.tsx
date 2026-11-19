"use client";

import { ChartBarIcon, XIcon } from "@phosphor-icons/react/ssr";
import { type ReactNode, useState } from "react";

const BUTTON =
  "border-border-surface bg-panel text-ink hover:border-ink-meta focus-visible:ring-brand-ring rounded-control text-label flex items-center gap-2 border px-2.5 py-2 focus-visible:ring-2 focus-visible:outline-none";

/**
 * The stats rail's frame (KAN-879): its cards under a Close button, or,
 * once closed, one Show Details button in the rail's place, so the tables
 * take the room. The cards are drawn on the server and passed in.
 */
// ponytail: closed is not kept across a reload; localStorage if the team asks.
export function ClosableRail({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(true);

  if (!open) {
    return (
      // A small tab on the window's right edge, out of the layout: as a column of its own, the
      // closed rail still took a strip of the page beside the tables.
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-expanded={false}
        aria-label="Show Details"
        title="Show Details"
        className="border-border-surface bg-panel text-ink hover:border-ink-meta focus-visible:ring-brand-ring rounded-l-control fixed top-24 right-0 z-10 border border-r-0 p-2 shadow-sm focus-visible:ring-2 focus-visible:outline-none"
      >
        <ChartBarIcon size={18} aria-hidden />
      </button>
    );
  }

  return (
    <aside className="flex shrink-0 flex-col gap-4 px-6 pb-8 lg:w-88 lg:overflow-y-auto lg:py-8 lg:pr-10 lg:pl-0">
      <div className="flex items-center justify-between">
        <h2 className="text-ink text-base font-semibold">Details</h2>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-expanded
          aria-label="Close Details"
          title="Close Details"
          className={BUTTON}
        >
          <XIcon size={18} aria-hidden />
        </button>
      </div>
      {children}
    </aside>
  );
}
