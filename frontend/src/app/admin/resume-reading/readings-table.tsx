"use client";

import { ListDashesIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { SparkleIcon } from "@/components/icons";
import { SelectField } from "@/components/ui/select-field";
import { Tip } from "@/components/ui/tip";
import { cn } from "@/lib/cn";
import { type RecentReading, reasonOf, routeName } from "@/lib/resume-reading";

import { count, when } from "../format";
import { READING_SECTIONS } from "../pages";
import { Panel, TD } from "../panel";
import { bySort, type Sort, SortHeads } from "../sort-heads";

const ALL = "all";
const READERS = [
  { value: ALL, label: "All Readers" },
  { value: "model", label: "AI" },
  { value: "parser", label: "Rule-Based Parser" },
];

const COLUMNS = [
  { key: "at", label: "Time (UTC)", numeric: false },
  { key: "account", label: "Account", numeric: false },
  { key: "route", label: "Route", numeric: false },
  { key: "read_by", label: "Read By", numeric: false },
  { key: "seconds", label: "Seconds", numeric: true },
  { key: "entries", label: "Entries", numeric: true },
  { key: "tokens", label: "Tokens", numeric: true },
] as const satisfies readonly { key: keyof RecentReading; label: string; numeric: boolean }[];
type SortKey = (typeof COLUMNS)[number]["key"];

/**
 * A student's account id, the first eight characters of it: the whole id is
 * its tooltip, and a press copies it, so an admin can find the student who
 * reported a problem. The whole id in the cell made the table 200px wider
 * than its card.
 */
function AccountId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Tip label={`Copy ${id}`}>
      <button
        type="button"
        aria-label={`Copy account ID ${id}`}
        onClick={async () => {
          await navigator.clipboard.writeText(id);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="text-ink-muted hover:text-ink focus-visible:ring-brand-ring rounded-xs tabular-nums focus-visible:ring-2 focus-visible:outline-none"
      >
        {/* The same width in both states, so the row holds still. */}
        <span aria-live="polite">{copied ? "Copied  " : id.slice(0, 8)}</span>
      </button>
    </Tip>
  );
}

/**
 * The period's newest readings (KAN-953), one line a row, sorted and
 * filtered as Board Reads is. Who read a resume and why share one cell (a
 * glyph, the reader, then the model or the reason), which keeps every row
 * one line and the table inside its card: a column each, with the reason in
 * a pill, gave nine columns, rows of two heights and a sideways scroll.
 * The time has no year, which the period's days already say, and the skills
 * a reading found are left out: the entries say whether it found anything,
 * and with both the table was 28px wider than its card at a 1440px window.
 */
export function ReadingsTable({ rows }: { rows: RecentReading[] }) {
  const [reader, setReader] = useState(ALL);
  const [reason, setReason] = useState(ALL);
  const [sort, setSort] = useState<Sort<SortKey>>({ key: "at", down: true });

  const reasons = [...new Set(rows.flatMap((r) => (r.reason ? [r.reason] : [])))].toSorted();
  // A pick can outlive its option: the reasons come from the period's rows, and the period
  // changes under this table. A reason the rows no longer hold counts as no pick.
  const held = reasons.includes(reason) ? reason : ALL;
  const shown = rows
    .filter((r) => (reader === ALL || r.read_by === reader) && (held === ALL || r.reason === held))
    .toSorted(bySort(sort));

  return (
    <Panel section={READING_SECTIONS.readings} bodyClassName="p-0">
      <div className="border-border-subtle flex flex-wrap items-end gap-4 border-b px-5 py-4">
        <SelectField
          id="readings-reader"
          label="Read By"
          value={reader}
          onValueChange={setReader}
          options={READERS}
          className="w-52"
        />
        <SelectField
          id="readings-reason"
          label="Reason"
          value={held}
          onValueChange={setReason}
          options={[
            { value: ALL, label: "All Reasons" },
            ...reasons.map((r) => ({ value: r, label: reasonOf(r).label })),
          ]}
          className="w-64"
        />
        <p className="text-note text-ink-meta ml-auto pb-2" aria-live="polite">
          Showing {shown.length} of {rows.length} rows
        </p>
      </div>
      {shown.length === 0 ? (
        <p className="text-body text-ink-muted p-5">
          {rows.length === 0
            ? "No resume was read in this period. Pick a longer one."
            : "No readings match these filters."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="text-body w-full border-collapse text-left">
            <thead>
              <tr className="border-border-subtle border-b whitespace-nowrap">
                <SortHeads columns={COLUMNS} sort={sort} onSort={setSort} />
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => {
                const ai = r.read_by === "model";
                const Icon = ai ? SparkleIcon : ListDashesIcon;
                const why = r.reason ? reasonOf(r.reason) : null;
                return (
                  <tr
                    key={`${r.at}:${r.account}:${r.route}`}
                    className="border-border-subtle text-ink border-b last:border-b-0"
                  >
                    <td className={cn(TD, "whitespace-nowrap tabular-nums")}>
                      {when(r.at).slice(5)}
                    </td>
                    <td className={TD}>
                      <AccountId id={r.account} />
                    </td>
                    <td className={cn(TD, "whitespace-nowrap")}>{routeName(r.route)}</td>
                    <td className={cn(TD, "whitespace-nowrap")}>
                      <span className="flex items-center gap-2">
                        <Icon
                          size={16}
                          aria-hidden
                          className={cn("shrink-0", ai ? "text-brand" : "text-ink-meta")}
                        />
                        <span className="font-medium">{ai ? "AI" : "Rule-Based Parser"}</span>
                        <span className={why?.fault ? "text-danger" : "text-ink-muted"}>
                          {ai ? r.model : why?.label}
                        </span>
                      </span>
                    </td>
                    <td className={cn(TD, "text-right tabular-nums")}>{r.seconds.toFixed(1)}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>{count(r.entries)}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>
                      {r.tokens === null ? "–" : count(r.tokens)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
