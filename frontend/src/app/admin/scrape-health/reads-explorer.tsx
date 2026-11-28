"use client";

import { CaretDownIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { SelectField } from "@/components/ui/select-field";
import { cn } from "@/lib/cn";
import type { ScrapeHealth } from "@/lib/fill-health";
import { systemName } from "@/lib/scrape-status";

import { count } from "../format";
import { SCRAPE_SECTIONS } from "../pages";
import { Panel, TD } from "../panel";
import { bySort, type Sort, SortHeads } from "../sort-heads";
import { Key } from "../day-columns";

/** The systems the first card shows before its arrow opens the rest. */
const FIRST = 5;
const ALL = "all";

const RESULTS = [
  { value: ALL, label: "All Results" },
  { value: "failed", label: "With Failed Reads" },
  { value: "clean", label: "No Failed Reads" },
];

type Row = ScrapeHealth["days"][number];
const COLUMNS = [
  { key: "day", label: "Day (UTC)", numeric: false },
  { key: "ats", label: "Hiring System", numeric: false },
  { key: "done", label: "Done", numeric: true },
  { key: "failed", label: "Failed", numeric: true },
  { key: "mean_seconds", label: "Mean Seconds", numeric: true },
  { key: "new_jobs", label: "New Jobs", numeric: true },
] as const satisfies readonly { key: keyof Row; label: string; numeric: boolean }[];
type SortKey = (typeof COLUMNS)[number]["key"];

/**
 * Scrape Health's two lower cards, which share one pick (KAN-879).
 *
 * BOARDS BY HIRING SYSTEM: one bar per system, most boards first. A bar's
 * length is the system's boards against the largest system's, and its dark
 * part the boards ever read; the row's figure says both, so nothing is read
 * by colour alone. Each row is a button that filters Board Reads to its
 * system, and a second press clears it. It lifts under the pointer because
 * it acts: the rows lifted before they did anything, which a design review
 * found promised a click that did nothing. The card shows the five largest
 * until Show All opens the rest. Bars, never a donut: 13 systems are
 * compared, and a donut's slices cannot be.
 *
 * BOARD READS: the window's reads per day (UTC) per hiring system, filtered
 * by hiring system and by whether a row has failed reads, and sorted by any
 * column. The rows are the page's own, so nothing here asks the API.
 */
export function ReadsExplorer({
  systems,
  rows,
}: {
  systems: ScrapeHealth["systems"];
  rows: Row[];
}) {
  const [open, setOpen] = useState(false);
  const [system, setSystem] = useState(ALL);
  const [result, setResult] = useState(ALL);
  const [sort, setSort] = useState<Sort<SortKey>>({ key: "day", down: true });

  const most = Math.max(...systems.map((s) => s.boards), 1);
  const more = systems.length - FIRST;
  // A picked system stays in view while the card is closed.
  const listed = open ? systems : systems.filter((s, i) => i < FIRST || s.ats === system);

  const shown = rows
    .filter(
      (r) =>
        (system === ALL || r.ats === system) &&
        (result === ALL || (result === "failed" ? r.failed > 0 : r.failed === 0)),
    )
    .toSorted(bySort(sort));

  return (
    <>
      <Panel
        section={SCRAPE_SECTIONS.systems}
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
        <p className="text-note text-ink-meta mb-3">
          Select a hiring system to filter Board Reads below.
        </p>
        <ul className="grid gap-3 @3xl/main:grid-cols-2">
          {listed.map((s) => {
            const picked = s.ats === system;
            return (
              <li key={s.ats}>
                <button
                  type="button"
                  aria-pressed={picked}
                  onClick={() => setSystem(picked ? ALL : s.ats)}
                  className={cn(
                    "rounded-control focus-visible:ring-brand-ring w-full border px-3.5 py-3 text-left transition duration-150 focus-visible:ring-2 focus-visible:outline-none",
                    // A shadow at rest, as every box on the page has, and WorkIt's lift
                    // (--shadow-lift, for a card that is one target) under the pointer.
                    "shadow-card hover:shadow-lift motion-safe:hover:-translate-y-0.5",
                    picked
                      ? "border-brand bg-brand-tint"
                      : "border-border-surface bg-panel hover:border-ink-meta",
                  )}
                >
                  <span className="text-body flex items-baseline justify-between gap-3">
                    <span className="text-ink font-medium">{systemName(s.ats)}</span>
                    <span className="text-ink-meta tabular-nums">
                      <span className="text-ink font-medium">{count(s.read)}</span> /{" "}
                      {count(s.boards)} read
                    </span>
                  </span>
                  <span
                    className="bg-brand-pale mt-2 block h-2 overflow-hidden rounded-r-xs"
                    style={{ width: `${Math.max((s.boards / most) * 100, 1)}%` }}
                  >
                    <span
                      className="bg-brand block h-full"
                      style={{ width: `${(s.read / s.boards) * 100}%` }}
                    />
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <p className="text-note text-ink-muted mt-4 flex flex-wrap justify-center gap-5">
          <Key swatch="bg-brand">Read</Key>
          <Key swatch="bg-brand-pale">Not Read Yet</Key>
        </p>
      </Panel>

      <Panel section={SCRAPE_SECTIONS.reads} bodyClassName="p-0">
        <div className="border-border-subtle flex flex-wrap items-end gap-4 border-b px-5 py-4">
          <SelectField
            id="reads-system"
            label="Hiring System"
            value={system}
            onValueChange={setSystem}
            options={[
              { value: ALL, label: "All Hiring Systems" },
              ...systems.map((s) => ({ value: s.ats, label: systemName(s.ats) })),
            ]}
            className="w-56"
          />
          <SelectField
            id="reads-result"
            label="Result"
            value={result}
            onValueChange={setResult}
            options={RESULTS}
            className="w-56"
          />
          <p className="text-note text-ink-meta ml-auto pb-2" aria-live="polite">
            Showing {shown.length} of {rows.length} rows
          </p>
        </div>
        {shown.length === 0 ? (
          <p className="text-body text-ink-muted p-5">
            {rows.length === 0
              ? "No board was read in this period. Move the period back, or pick a longer one."
              : "No board reads match these filters."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="text-body w-full border-collapse text-left">
              <thead>
                <tr className="border-border-subtle border-b">
                  <SortHeads columns={COLUMNS} sort={sort} onSort={setSort} />
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr
                    key={`${r.day}:${r.ats}`}
                    className="border-border-subtle text-ink border-b last:border-b-0"
                  >
                    <td className={cn(TD, "whitespace-nowrap")}>{r.day}</td>
                    <td className={cn(TD, "font-medium")}>{systemName(r.ats)}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>{count(r.done)}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>
                      {r.failed > 0 ? (
                        <span className="bg-danger-tint text-danger rounded-full px-2 py-0.5 font-medium">
                          {count(r.failed)}
                        </span>
                      ) : (
                        0
                      )}
                    </td>
                    <td className={cn(TD, "text-right tabular-nums")}>
                      {r.mean_seconds === null ? "-" : r.mean_seconds.toFixed(1)}
                    </td>
                    <td className={cn(TD, "text-right tabular-nums")}>{count(r.new_jobs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
