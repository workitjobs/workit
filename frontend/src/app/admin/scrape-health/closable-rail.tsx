"use client";

import { ChartBarIcon, XIcon } from "@phosphor-icons/react/ssr";
import { type ReactNode, useState } from "react";

const BUTTON =
  "border-border-surface bg-panel text-ink hover:border-ink-meta focus-visible:ring-brand-ring rounded-control text-label flex items-center gap-2 border px-2.5 py-2 focus-visible:ring-2 focus-visible:outline-none";

/**
 * The stats rail's frame (KAN-879): its cards under a Close button, or,
 * once closed, one Show Stats button in the rail's place, so the tables
 * take the room. The cards are drawn on the server and passed in.
 */
// ponytail: closed is not kept across a reload; localStorage if the team asks.
export function ClosableRail({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(true);

  if (!open) {
    return (
      <aside className="shrink-0 px-6 pb-8 lg:py-8 lg:pr-10 lg:pl-0">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={false}
          className={BUTTON}
        >
          <ChartBarIcon size={18} aria-hidden />
          Show Stats
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex shrink-0 flex-col gap-4 px-6 pb-8 lg:w-88 lg:overflow-y-auto lg:py-8 lg:pr-10 lg:pl-0">
      <div className="flex items-center justify-between">
        <h2 className="text-title text-ink">Stats</h2>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-expanded
          aria-label="Close Stats"
          title="Close Stats"
          className={BUTTON}
        >
          <XIcon size={18} aria-hidden />
        </button>
      </div>
      {children}
    </aside>
  );
}
