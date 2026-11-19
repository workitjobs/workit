"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import type { ScrapeHealth } from "@/lib/fill-health";

import { Panel, TD, TH } from "../panel";

const SELECT =
  "border-border-control bg-panel text-body text-ink focus-visible:ring-brand-ring rounded-control border px-2.5 py-1.5 capitalize focus-visible:ring-2 focus-visible:outline-none";

const RESULTS = {
  all: "All Results",
  failed: "With Failed Reads",
  clean: "No Failed Reads",
} as const;
type Result = keyof typeof RESULTS;

/**
 * Board Reads (KAN-879): the period's reads per day (UTC) per hiring
 * system, filtered in the browser by hiring system and by whether a row has
 * failed reads. The rows are the page's own, so a filter asks the API
 * nothing; the period is the page's day pills.
 */
export function ReadsTable({ rows }: { rows: ScrapeHealth["days"] }) {
  const [system, setSystem] = useState("");
  const [result, setResult] = useState<Result>("all");
  const systems = [...new Set(rows.map((r) => r.ats))].sort();
  const shown = rows.filter(
    (r) =>
      (!system || r.ats === system) &&
      (result === "all" || (result === "failed" ? r.failed > 0 : r.failed === 0)),
  );

  return (
    <Panel
      title="Board Reads"
      bodyClassName="p-0"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Hiring System"
            value={system}
            onChange={(e) => setSystem(e.target.value)}
            className={SELECT}
          >
            <option value="">All Hiring Systems</option>
            {systems.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            aria-label="Result"
            value={result}
            onChange={(e) => setResult(e.target.value as Result)}
            className={SELECT}
          >
            {Object.entries(RESULTS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      }
    >
      {shown.length === 0 ? (
        <p className="text-body text-ink-muted p-5">
          {rows.length === 0
            ? "No board reads in this period."
            : "No board reads match these filters."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="text-body w-full border-collapse text-left">
            <thead>
              <tr className="border-border-subtle border-b">
                <th className={TH}>Day (UTC)</th>
                <th className={TH}>Hiring System</th>
                <th className={cn(TH, "text-right")}>Done</th>
                <th className={cn(TH, "text-right")}>Failed</th>
                <th className={cn(TH, "text-right")}>Mean Seconds</th>
                <th className={cn(TH, "text-right")}>New Jobs</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={`${r.day}:${r.ats}`}
                  className="border-border-subtle text-ink hover:bg-hover border-b last:border-b-0"
                >
                  <td className={cn(TD, "whitespace-nowrap")}>{r.day}</td>
                  <td className={cn(TD, "font-medium capitalize")}>{r.ats}</td>
                  <td className={cn(TD, "text-right tabular-nums")}>{r.done}</td>
                  <td className={cn(TD, "text-right tabular-nums")}>
                    {r.failed > 0 ? (
                      <span className="bg-danger-tint text-danger rounded-full px-2 py-0.5 font-medium">
                        {r.failed}
                      </span>
                    ) : (
                      0
                    )}
                  </td>
                  <td className={cn(TD, "text-right tabular-nums")}>
                    {r.mean_seconds === null ? "-" : r.mean_seconds.toFixed(1)}
                  </td>
                  <td className={cn(TD, "text-right tabular-nums")}>
                    {r.new_jobs.toLocaleString("en-US")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 0 && (
        <p className="border-border-subtle text-label text-ink-meta border-t px-5 py-3 font-normal">
          Showing {shown.length} of {rows.length} rows
        </p>
      )}
    </Panel>
  );
}
