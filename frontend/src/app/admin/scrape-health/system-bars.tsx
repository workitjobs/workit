"use client";

import { CaretDownIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { cn } from "@/lib/cn";
import type { ScrapeHealth } from "@/lib/fill-health";

import { Panel } from "../panel";

const count = (n: number) => n.toLocaleString("en-US");
/** The systems the card shows before its arrow opens the rest. */
const FIRST = 5;

function Key({ swatch, children }: { swatch: string; children: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`size-2.5 rounded-sm ${swatch}`} aria-hidden />
      {children}
    </span>
  );
}

/**
 * The catalog's boards per hiring system, most first (KAN-879): each bar's
 * length is the system's boards against the largest system's, and its dark
 * part the boards ever read. A row's figure says both, so no part is read
 * by colour alone. The card shows the five largest; its arrow opens the
 * rest, so the card is no taller than the chart beside it until asked.
 * Bars, not a donut: the systems are compared, and a donut's slices cannot
 * be.
 */
export function SystemBars({ systems }: { systems: ScrapeHealth["systems"] }) {
  const [open, setOpen] = useState(false);
  const most = Math.max(...systems.map((s) => s.boards), 1);
  const more = systems.length - FIRST;
  const shown = open ? systems : systems.slice(0, FIRST);

  return (
    <Panel
      title="Boards by Hiring System"
      className="@4xl:col-span-2"
      action={
        more > 0 && (
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            className="text-label text-ink-muted hover:text-ink focus-visible:ring-brand-ring rounded-control flex items-center gap-1.5 px-2 py-1 focus-visible:ring-2 focus-visible:outline-none"
          >
            {open ? "Show Fewer" : `Show All ${systems.length}`}
            <CaretDownIcon
              size={16}
              aria-hidden
              className={cn("transition-transform", open && "rotate-180")}
            />
          </button>
        )
      }
    >
      <ul className="space-y-3">
        {shown.map((s) => (
          <li key={s.ats}>
            <div className="text-body flex items-baseline justify-between gap-3">
              <span className="text-ink font-medium capitalize">{s.ats}</span>
              <span className="text-ink-meta tabular-nums">
                <span className="text-ink font-medium">{count(s.read)}</span> / {count(s.boards)}
              </span>
            </div>
            <div
              className="bg-brand-pale mt-1.5 h-2 overflow-hidden rounded-r-sm"
              style={{ width: `${Math.max((s.boards / most) * 100, 1)}%` }}
              title={`${count(s.read)} of ${count(s.boards)} boards read`}
            >
              <div className="bg-brand h-full" style={{ width: `${(s.read / s.boards) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-label text-ink-muted mt-5 flex flex-wrap justify-center gap-5 font-normal">
        <Key swatch="bg-brand">Read</Key>
        <Key swatch="bg-brand-pale">Not Read Yet</Key>
      </p>
    </Panel>
  );
}
