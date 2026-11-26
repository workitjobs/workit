"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SelectField } from "@/components/ui/select-field";
import { cn } from "@/lib/cn";
import {
  ALL_FILLS,
  type FillFilters,
  type FillHealthRow,
  matchesFilters,
  NO_FILL_FILTERS,
  percent,
} from "@/lib/fill-health";
import { systemName, type Window, windowHref } from "@/lib/scrape-status";

import { count } from "../format";
import { FILL_SECTIONS } from "../pages";
import { Panel, TD, TH } from "../panel";
import { bySort, type Sort, SortHeads } from "../sort-heads";

const NEEDS_YOU = [
  { value: ALL_FILLS, label: "Any Rate" },
  { value: "0.1", label: "10% or More" },
  { value: "0.25", label: "25% or More" },
  { value: "0.5", label: "50% or More" },
];

const COLUMNS = [
  { key: "day", label: "Day (UTC)", numeric: false },
  { key: "job_system", label: "Job System", numeric: false },
  { key: "fills", label: "Fills", numeric: true },
  { key: "clean_share", label: "No Failed Field", numeric: true },
  { key: "needs_you_rate", label: "Needs You Rate", numeric: true },
] as const satisfies readonly { key: keyof FillHealthRow; label: string; numeric: boolean }[];
type SortKey = (typeof COLUMNS)[number]["key"];

/**
 * Fill Health's table (KAN-879): the window's fills per day (UTC) per job
 * system, as Scrape Health's Board Reads is. Job System, Needs You Rate and
 * Errors filter the rows the page already holds, so a pick asks nothing.
 * Engine Version is the API's own filter (it changes every number), so its
 * pick opens the page's address with it, and the window's links keep it.
 * Top Errors has no sort: it is a list of names, not one value.
 */
export function FillsTable({
  rows,
  versions,
  version,
  window,
}: {
  /** The window's rows. */
  rows: FillHealthRow[];
  /** The engine versions the API saw in its period. */
  versions: string[];
  /** The engine version in the address, or "". */
  version: string;
  window: Window;
}) {
  const router = useRouter();
  const [filters, setFilters] = useState(NO_FILL_FILTERS);
  const [sort, setSort] = useState<Sort<SortKey>>({ key: "day", down: true });

  const systems = [...new Set(rows.map((r) => r.job_system))].toSorted();
  const errorNames = [...new Set(rows.flatMap((r) => r.top_errors.map((e) => e.name)))].toSorted();
  // A pick can outlive its option: the options come from the window's rows, and the window
  // moves under this table. A pick the rows no longer hold counts as no pick, or the table
  // would say nothing matches while rows exist.
  const held: FillFilters = {
    ...filters,
    system: systems.includes(filters.system) ? filters.system : ALL_FILLS,
    errors:
      filters.errors.startsWith("name:") && !errorNames.includes(filters.errors.slice(5))
        ? ALL_FILLS
        : filters.errors,
  };
  const shown = rows.filter((r) => matchesFilters(r, held)).toSorted(bySort(sort));

  return (
    <Panel section={FILL_SECTIONS.fills} bodyClassName="p-0">
      <div className="border-border-subtle flex flex-wrap items-end gap-4 border-b px-5 py-4">
        <SelectField
          id="fills-system"
          label="Job System"
          value={held.system}
          onValueChange={(system) => setFilters({ ...filters, system })}
          options={[
            { value: ALL_FILLS, label: "All Job Systems" },
            ...systems.map((s) => ({ value: s, label: systemName(s) })),
          ]}
          className="w-48"
        />
        <SelectField
          id="fills-needs-you"
          label="Needs You Rate"
          value={filters.needsYou}
          onValueChange={(needsYou) => setFilters({ ...filters, needsYou })}
          options={NEEDS_YOU}
          className="w-44"
        />
        <SelectField
          id="fills-errors"
          label="Errors"
          value={held.errors}
          onValueChange={(errors) => setFilters({ ...filters, errors })}
          options={[
            { value: ALL_FILLS, label: "Any" },
            { value: "with", label: "With Errors" },
            { value: "none", label: "No Errors" },
            ...errorNames.map((name) => ({ value: `name:${name}`, label: name })),
          ]}
          className="w-52"
        />
        <SelectField
          id="fills-version"
          label="Engine Version"
          value={version || ALL_FILLS}
          onValueChange={(picked) =>
            router.push(
              windowHref(window, "/admin/fill-health", {
                engine_version: picked === ALL_FILLS ? "" : picked,
              }),
            )
          }
          options={[{ value: ALL_FILLS, label: "All Versions" }, ...versions]}
          className="w-52"
        />
        <p className="text-note text-ink-meta ml-auto pb-2" aria-live="polite">
          Showing {shown.length} of {rows.length} rows
        </p>
      </div>
      {shown.length === 0 ? (
        <p className="text-body text-ink-muted p-5">
          {rows.length === 0
            ? "No fills in this period. Move the period back, or pick a longer one."
            : "No fills match these filters."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="text-body w-full border-collapse text-left">
            <thead>
              <tr className="border-border-subtle border-b">
                <SortHeads columns={COLUMNS} sort={sort} onSort={setSort} />
                <th className={cn(TH, "font-normal")}>Top Errors</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={`${r.day}:${r.job_system}`}
                  className="border-border-subtle text-ink border-b align-top last:border-b-0"
                >
                  <td className={cn(TD, "whitespace-nowrap")}>{r.day}</td>
                  <td className={cn(TD, "font-medium")}>{systemName(r.job_system)}</td>
                  <td className={cn(TD, "text-right tabular-nums")}>{count(r.fills)}</td>
                  <td className={cn(TD, "text-right tabular-nums")}>{percent(r.clean_share)}</td>
                  <td className={cn(TD, "text-right tabular-nums")}>{percent(r.needs_you_rate)}</td>
                  <td className={TD}>
                    {r.top_errors.length === 0 ? (
                      <span className="text-ink-meta">None</span>
                    ) : (
                      <span className="flex flex-wrap gap-1.5">
                        {r.top_errors.map((e) => (
                          <span
                            key={e.name}
                            className="bg-danger-tint text-danger text-note rounded-full px-2 py-0.5 whitespace-nowrap tabular-nums"
                          >
                            {e.name} {count(e.count)}
                          </span>
                        ))}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
