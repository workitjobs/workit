"use client";

import {
  CheckIcon,
  ClockIcon,
  PencilLineIcon,
  ProhibitIcon,
  WarningIcon,
} from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useCallback, useState, type ReactNode } from "react";

import { ClickableRow } from "@/components/clickable-row";
import { CompanyLogo } from "@/components/company-logo";
import { PlusIcon } from "@/components/icons";
import { MatchBadge } from "@/components/match-badge";
import { Reflow } from "@/components/reflow";
import { GroupHeadingRow, useFolds } from "@/components/table-group";
import { PickBox } from "@/components/selection-bar";
import { Checkbox } from "@/components/shadcn/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/shadcn/table";
import { STICKY_HEAD, STICKY_TH, TABLE_FILL, useFillPage } from "@/components/fill-page";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { BatchTabState } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";
import { MATCH_TIERS, matchTier } from "@/lib/match";

import { ResumeViewButton } from "../jobs/[jobId]/tailor/resume-preview";
import { LocalDate } from "../local-time";
import { ALIGN, TD, TH, type ActivityItem } from "./activity-list";
import type { QueueGroupBy } from "./queue-layout";
import { RowMenu } from "./row-menu";

/** Whether WorkIt has started an Up Next job: In Progress (opened in a
 *  batch tab, whether the tab is still open or not) or Queued (not yet).
 *  Two groups since 2026-10-29: a third, Incomplete, held started jobs
 *  whose tab was closed, and split one kind of job in two (it was named
 *  Unfinished, and In Your Tabs and Waiting were the others, before that). */
export type QueueGroup = "progress" | "queued" | "closed";

/** An Up Next row: the job, its batch tab's state (`tab`, null with no tab
 *  open), whether its tab was closed before its submit was seen
 *  (`tabClosed`, KAN-512), and the group that puts it in. */
export type QueueRow = ActivityItem & {
  tab: BatchTabState | null;
  tabClosed: boolean;
  group: QueueGroup;
};

/** A job's group: started once a tab is open on it, once its tab was closed
 *  unsubmitted, or once its fill left it needs_you (its tab since closed). */
export function groupOf(
  item: ActivityItem,
  tab: BatchTabState | null,
  tabClosed = false,
): QueueGroup {
  // A closed posting can never go out, so it waits in a group of its own
  // at the foot (2026-11-10), not in Queued, where it read as waiting its
  // turn.
  if (item.closed) return "closed";
  return tab || tabClosed || item.status === "failed" ? "progress" : "queued";
}

/** Whether Auto Apply can open the row: no tab open on it, and its posting open. */
export function canOpen(row: QueueRow): boolean {
  return row.tab == null && !row.closed;
}

/** The groups in the order the table shows them. A line beside each name
 *  ("Filling now, or waiting for your Submit") was cut as noise (2026-10-29):
 *  the name, the count and the rows' statuses say it. */
const GROUP_ORDER: { id: QueueGroup; label: string }[] = [
  { id: "progress", label: "In Progress" },
  { id: "queued", label: "Queued" },
  { id: "closed", label: "Posting Closed" },
];

/** A row's match band, as Group By Match and the Match filter read it
 *  (./queue-filters.tsx): its tier's name (lib/match.ts), or Not Scored. */
export const NOT_SCORED = "Not Scored";
export const MATCH_KEYS = [...MATCH_TIERS, NOT_SCORED];
export function matchKey(score: number | null) {
  return score == null ? NOT_SCORED : matchTier(score);
}

/** One heading's rows; a null label draws no heading (Group By None). */
type Section = { id: string; label: string | null; rows: QueueRow[] };

/** The table's headings and the rows under each, by Group By (Table
 *  Settings, ./queue-layout.ts), each in the queue's order. A group with no
 *  rows draws no heading. */
function sectionsOf(rows: QueueRow[], by: QueueGroupBy): Section[] {
  if (by === "none") return [{ id: "all", label: null, rows }];
  const sections =
    by === "status"
      ? GROUP_ORDER.map(({ id, label }) => ({
          id,
          label,
          rows: rows.filter((row) => row.group === id),
        }))
      : MATCH_KEYS.map((key) => ({
          id: key,
          label: key,
          rows: rows.filter((row) => matchKey(row.match) === key),
        }));
  return sections.filter((section) => section.rows.length > 0);
}

/** A batch tab's state as the row's status: a word in its colour, with
 *  its glyph. Plain text, not a pill: the group already names the state in
 *  a pill, and two pills per row read as noise. */
const TAB_STATUS: Record<BatchTabState, { label: string; ink: string; Icon: typeof CheckIcon }> = {
  filling: { label: "Filling", ink: "text-advanced", Icon: PencilLineIcon },
  ready: { label: "Ready to Submit", ink: "text-positive-ink", Icon: CheckIcon },
  needs_you: { label: "Needs Your Input", ink: "text-warning", Icon: WarningIcon },
  failed: { label: "Fill Failed", ink: "text-danger", Icon: WarningIcon },
  applied: { label: "Submitted", ink: "text-brand", Icon: CheckIcon },
};

/** Match and Date Added fold into the Role cell below @3xl/main (KAN-567):
 *  their columns close to no width and Role, the leftover column, takes what
 *  they free (456px of the 960px table). Closed, not removed: the group
 *  heading's `colSpan` counts six columns, and a missing one would hand
 *  Role's width to an empty slot. Below @xl/main (a phone) the table is
 *  752px instead (TABLE_WIDTH), so Role keeps 248px: at 456px it ran past
 *  the card and the ⋯ column covered the end of a long title. */
/** The columns whose cells are one control or score each (View, a match
 *  pill): centred under a centred heading, by the table rule in
 *  frontend/docs/design.md. Text columns stay left-aligned. */
const CENTRED = new Set(["resume", "match"]);

const COLUMNS: { id: string; label: string; width?: string; folds?: boolean }[] = [
  { id: "role", label: "Job" },
  // "Ready to Submit · Review" with its glyph, about 200px.
  { id: "status", label: "Status", width: "w-60" },
  { id: "resume", label: "Resume", width: "w-52" },
  { id: "match", label: "Match", width: "w-0 @3xl/main:w-24", folds: true },
  { id: "added", label: "Date Added", width: "w-0 @3xl/main:w-28", folds: true },
  { id: "menu", label: "More", width: "w-14" },
];

/** Role is frozen at the left from @3xl/main, not from @2xl/main as Live
 *  Activity's (FROZEN in ./activity-list.tsx): below that it is wide with
 *  the folded columns' width, and frozen it covered most of the card, so
 *  Status and Resume scrolled by behind it in a strip. */
const ROLE_FROZEN =
  "z-1 bg-panel @3xl/main:sticky @3xl/main:left-0 @3xl/main:shadow-[1px_0_0_var(--color-border-subtle)]";

/** The frozen Role heading's and the ⋯ heading's edges with the heading's
 *  rule under them, as `STICKY_TH_FROZEN` draws a frozen heading's. */
const ROLE_HEAD_EDGE =
  "@3xl/main:shadow-[inset_0_-1px_0_var(--color-border-subtle),1px_0_0_var(--color-border-subtle)]";
const MENU_HEAD_EDGE =
  "in-data-clipped:shadow-[inset_0_-1px_0_var(--color-border-subtle),-1px_0_0_var(--color-border-subtle),-8px_0_12px_-4px_rgb(18_26_40/0.2)]";

const TABLE_WIDTH = "min-w-[47rem] @xl/main:min-w-[60rem]";

/** A folded column's cell: no padding while it is closed, its content hidden. */
const FOLDS = "px-0 @3xl/main:px-4";
const FOLDED = "hidden @3xl/main:inline";

/** The ⋯ column stays at the right edge while the table scrolls, at every
 *  width, so a row's menu (Remove is only there) is always in reach. While
 *  columns are hidden past that edge (`data-clipped` on the card,
 *  `useClipped`) it draws an edge shadow, the cue that the table scrolls. */
const STICKY_END =
  "sticky right-0 z-1 bg-panel in-data-clipped:shadow-[-1px_0_0_var(--color-border-subtle),-8px_0_12px_-4px_rgb(18_26_40/0.2)]";

/** A sticky cell paints the row's own background so scrolled cells don't
 *  show through it, so it follows the row's tint: picked, hovered, or with
 *  its ⋯ menu open (`data-popup-open` on the trigger: the pointer leaves for
 *  the menu, and a sticky cell alone kept its hover tint). */
function stickyTint(picked: boolean) {
  return picked
    ? "bg-brand-tint"
    : "group-hover/row:bg-hover [tr:has([data-popup-open])_&]:bg-hover";
}

/** Whether the table hides columns past its right edge, kept current as it
 *  scrolls and resizes. Returns the flag and the ref for the `<table>`; its
 *  parent is the scrolling box (`shadcn/table.tsx`). */
function useClipped() {
  const [clipped, setClipped] = useState(false);
  const ref = useCallback((table: HTMLTableElement | null) => {
    const box = table?.parentElement;
    if (!table || !box) return;
    const measure = () => setClipped(box.scrollLeft + box.clientWidth < box.scrollWidth - 1);
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    observer.observe(table);
    box.addEventListener("scroll", measure, { passive: true });
    return () => {
      observer.disconnect();
      box.removeEventListener("scroll", measure);
    };
  }, []);
  return [clipped, ref] as const;
}

/**
 * Up Next's table (./up-next.tsx): every queued job under the headings
 * Table Settings' Group By picks (`groupBy`, ./queue-layout.ts: Status, the
 * default, Match or None), each the shared heading row with its name and
 * count, which folds it (components/table-group.tsx). By Status:
 *
 *   In Progress    started: open in a batch tab, with the tab's own state
 *                  (Filling, Ready to Submit, Needs You, Fill Failed), read
 *                  live from the extension (useBrowserTabs), or Needs You
 *                  once its tab closed (stage needs_you); a click opens it again
 *   Queued         not started, in the order the extension takes them
 *
 * The status says only where the job is. What it lacks shows where it is
 * fixed: no resume is an empty Choose Resume slot in the Resume cell, and
 * written questions are the status (a click goes to the tab), and Up
 * Next's heading links to Written Answers (./up-next.tsx).
 *
 * A row's status is its one action (a click goes where it is finished),
 * and the same ⋯ menu sits on every row
 * (./row-menu.tsx). Its Role cell starts with a select box, and Role's
 * heading with Select All, which unpicks every row while any is picked; a
 * box's click stops in its cell, or the row opens the job posting.
 */
export function QueueTable({
  rows,
  groupBy,
  picked,
  onPick,
  onAction,
  onResume,
  onRemove,
  onRemoveAll,
}: {
  rows: QueueRow[];
  /** How the rows go under headings (./queue-layout.ts). */
  groupBy: QueueGroupBy;
  picked: ReadonlySet<string>;
  onPick: (ids: string[]) => void;
  /** The row's one action (`actionOf`). */
  onAction: (row: QueueRow) => void;
  onResume: (row: QueueRow) => void;
  onRemove: (row: QueueRow) => void;
  /** Every closed posting's job out of the queue at once, from its group's
   *  heading (with Undo, as Remove is). */
  onRemoveAll?: (rows: QueueRow[]) => void;
}) {
  const [folded, fold] = useFolds();
  const [clipped, tableRef] = useClipped();
  // The queue scrolls inside its card, down to the page's foot, so the setup
  // row and Up Next's heading stay in view (components/fill-page.ts).
  const fill = useFillPage();
  const all = rows.length > 0 && rows.every((row) => picked.has(row.id));
  const some = rows.some((row) => picked.has(row.id));

  function pick(row: QueueRow, on: boolean) {
    onPick(on ? [...picked, row.id] : [...picked].filter((id) => id !== row.id));
  }

  return (
    <Card padding="none" className="mt-4 overflow-hidden" data-clipped={clipped || undefined}>
      <Table
        ref={tableRef}
        containerRef={fill}
        containerClassName={TABLE_FILL}
        className={cn(TABLE_WIDTH, "table-fixed")}
      >
        <TableHeader className={STICKY_HEAD}>
          <TableRow className="hover:bg-transparent">
            {COLUMNS.map((column) => (
              <TableHead
                key={column.id}
                className={cn(
                  TH,
                  STICKY_TH,
                  column.width,
                  column.id === "role"
                    ? ROLE_FROZEN
                    : CENTRED.has(column.id)
                      ? "text-center"
                      : ALIGN,
                  column.folds && FOLDS,
                  column.id === "menu" && STICKY_END,
                  // Sticky on both axes: over the rows and the other headings.
                  (column.id === "role" || column.id === "menu") && "z-3",
                  // Their edge and the heading's rule at once: one shadow
                  // replaces another (components/fill-page.ts).
                  column.id === "role" && ROLE_HEAD_EDGE,
                  column.id === "menu" && MENU_HEAD_EDGE,
                )}
              >
                {column.id === "role" ? (
                  <span className="flex items-center gap-3">
                    <PickBox>
                      <Checkbox
                        className="border-ink-meta"
                        checked={all}
                        indeterminate={some && !all}
                        // As the Inbox's: a click picks every row, or unpicks while any is picked,
                        // which is how a pick is cleared (the bar has no Clear).
                        onCheckedChange={() => onPick(some ? [] : rows.map((row) => row.id))}
                        aria-label={some ? "Unselect All" : "Select All"}
                      />
                    </PickBox>
                    {column.label}
                  </span>
                ) : column.id === "menu" ? (
                  <span className="sr-only">{column.label}</span>
                ) : column.folds ? (
                  <span className={FOLDED}>{column.label}</span>
                ) : (
                  column.label
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>

        <TableBody>
          {sectionsOf(rows, groupBy).map(({ id, label, rows: members }) => {
            const open = label == null || !folded.has(id);
            return [
              // The shared heading (components/table-group.tsx); Posting
              // Closed's with Remove All.
              label != null && (
                <GroupHeadingRow
                  key={id}
                  colSpan={COLUMNS.length}
                  label={label}
                  count={members.length}
                  open={open}
                  onToggle={() => fold(id)}
                  action={
                    id === "closed" &&
                    onRemoveAll && (
                      <Button variant="section" onClick={() => onRemoveAll(members)}>
                        Remove All
                      </Button>
                    )
                  }
                />
              ),
              ...(open
                ? members.map((row, i) => (
                    <Reflow key={row.id}>
                      <Row
                        row={row}
                        index={i}
                        byStatus={groupBy === "status"}
                        picked={picked.has(row.id)}
                        onPick={pick}
                        onAction={onAction}
                        onResume={onResume}
                        onRemove={onRemove}
                      />
                    </Reflow>
                  ))
                : []),
            ];
          })}
        </TableBody>
      </Table>
    </Card>
  );
}

function Row({
  row,
  index,
  byStatus,
  picked,
  onPick,
  onAction,
  onResume,
  onRemove,
}: {
  row: QueueRow;
  index: number;
  /** The rows sit under Status headings, which say Queued and Posting
   *  Closed, so their cells need not. */
  byStatus: boolean;
  picked: boolean;
  onPick: (row: QueueRow, on: boolean) => void;
  onAction: (row: QueueRow) => void;
  onResume: (row: QueueRow) => void;
  onRemove: (row: QueueRow) => void;
}) {
  const cells: ReactNode = (
    <>
      <TableCell className={cn(TD, ROLE_FROZEN, "transition-colors", stickyTint(picked))}>
        <div className="flex min-w-0 items-center gap-3">
          <PickBox>
            <Checkbox
              className="border-ink-meta"
              checked={picked}
              onCheckedChange={(on) => onPick(row, on === true)}
              aria-label={`Select ${row.role} at ${row.company}`}
            />
          </PickBox>
          <CompanyLogo
            name={row.company}
            src={row.logoUrl}
            className="text-meta size-8 shrink-0 rounded"
          />
          <div className="min-w-0">
            {/* The title wraps rather than cutting off (KAN-567): Role is the leftover column, about
                248px at 1024, and a cut title read whole only in a tooltip, which touch and keyboard
                never get. */}
            {row.href ? (
              <Link
                href={row.href}
                className="text-label text-ink hover:text-brand focus-visible:ring-brand-ring block rounded-xs font-semibold wrap-break-word whitespace-normal transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
              >
                {row.role}
              </Link>
            ) : (
              <p className="text-label text-ink font-semibold wrap-break-word whitespace-normal">
                {row.role}
              </p>
            )}
            <p className="text-note text-ink-meta flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="truncate" title={row.company}>
                {row.company}
              </span>
              {/* Match and Date Added, here while their columns are closed (COLUMNS); under the
                  company where the line has no room. */}
              <span className="flex shrink-0 items-center gap-2 @3xl/main:hidden">
                {row.match != null && <MatchBadge score={row.match} />}
                <span>
                  Added <LocalDate at={row.addedAt} />
                </span>
              </span>
            </p>
          </div>
        </div>
      </TableCell>

      <TableCell className={cn(TD, ALIGN, "overflow-hidden")}>
        <Status row={row} byStatus={byStatus} onAction={onAction} />
      </TableCell>

      <TableCell className={cn(TD, "overflow-hidden py-0 text-center")}>
        {/* View, as the Tracker's Resume column says it, not the resume's
            name: "Resume #6" on every row blended into one grey pill
            (2026-11-10). Change Resume is in the row's ⋯ menu. A button,
            so the row's own click (it opens the job) leaves it alone
            (components/clickable-row.tsx). */}
        {row.resume && row.resumeKey ? (
          <ResumeViewButton name={row.resume} resumeKey={row.resumeKey} />
        ) : (
          // A text button, as View is: a table row holds no bordered or
          // dashed controls (frontend/docs/design.md, buttons). It was a
          // dashed pill, beside View's text in the same column.
          <Button variant="ghost" size="sm" onClick={() => onResume(row)} title="Choose a resume">
            <PlusIcon aria-hidden />
            Choose Resume
          </Button>
        )}
      </TableCell>

      <TableCell className={cn(TD, "text-center", FOLDS)}>
        <span className={FOLDED}>
          {row.match != null ? (
            <MatchBadge score={row.match} />
          ) : (
            <span className="text-ink-faint">
              <span aria-hidden="true">–</span>
              <span className="sr-only">Not scored</span>
            </span>
          )}
        </span>
      </TableCell>

      <TableCell className={cn(TD, ALIGN, FOLDS)}>
        <span className={FOLDED}>
          <LocalDate at={row.addedAt} />
        </span>
      </TableCell>

      <TableCell
        className={cn(TD, "text-center", STICKY_END, "py-0 transition-colors", stickyTint(picked))}
      >
        {row.tab !== "applied" && <RowMenu item={row} onResume={onResume} onRemove={onRemove} />}
      </TableCell>
    </>
  );

  // Fades in down the table on arrival, 25ms apart, as the Applications list's rows do.
  const style = { animationDelay: `${Math.min(index, 10) * 25}ms` };
  return row.href ? (
    <ClickableRow
      href={row.href}
      className={cn(
        "animate-fade",
        picked
          ? "bg-brand-tint hover:bg-brand-tint"
          : "hover:bg-hover has-[[data-popup-open]]:bg-hover",
      )}
      style={style}
    >
      {cells}
    </ClickableRow>
  ) : (
    // No `group/row`: a row that opens nothing takes no hover tint (activity-list.tsx says why).
    <TableRow
      className={cn(
        "animate-fade",
        picked
          ? "bg-brand-tint hover:bg-brand-tint"
          : "has-[[data-popup-open]]:bg-hover hover:bg-transparent",
      )}
      style={style}
    >
      {cells}
    </TableRow>
  );
}

/**
 * The row's status: ONE item, never a second line, and a button where
 * there is somewhere to go. Most urgent first:
 *
 *   Posting Closed          red; nothing to open (Remove is in the ⋯ menu)
 *   N Questions to Write    amber, while any wait; Filling outranks it
 *   the tab's state         Filling (with a spinning ring), Ready to
 *                           Submit, Needs You, Fill Failed, Submitted
 *   Tab Closed, Not         a job whose batch tab the student closed before
 *   Submitted               WorkIt saw its submit (KAN-512): amber, one item
 *   Needs You               any other started job whose tab was closed
 *   (nothing)               a queued job, whatever it holds: its group's
 *                           name says it, and its questions show once it
 *                           starts (they can be written ahead on Written
 *                           Answers)
 *
 * A click goes where the student finishes it (`onAction`, ./up-next.tsx):
 * the job's tab, opened again if it was closed.
 *
 * TOO MANY LAYERS (2026-10-29). Each row had a pill badge, then a state with
 * an action link after it ("Tab Closed · Reopen") and the questions' link on
 * a second line; the user found the layers of text cluttered. "Tab Closed"
 * said a browser detail, and Reopen and the questions' link went to the same
 * place. A place in the queue ("#1 in Queue") was cut before that: five
 * fill at once, so the order read as one at a time.
 */
function Status({
  row,
  byStatus,
  onAction,
}: {
  row: QueueRow;
  byStatus: boolean;
  onAction: (row: QueueRow) => void;
}) {
  // Its group, Posting Closed, says it (2026-11-10), as Queued's name says
  // a queued job's state; under another Group By the cell says it, in ink
  // so it stands out, as the Tracker's black Posting Closed pill does.
  if (row.closed) {
    return byStatus ? null : (
      <PlainStatus Icon={ProhibitIcon} label="Posting Closed" ink="text-ink" />
    );
  }

  let label: string;
  let ink: string;
  let glyph: ReactNode;
  // A queued job shows no questions: they wait for it to start (asked for 2026-10-29), though they
  // can be written ahead on Written Answers.
  if (row.group === "queued") {
    return byStatus ? null : <PlainStatus Icon={ClockIcon} label="Queued" ink="text-ink-meta" />;
  }
  if (row.questions && row.tab !== "filling" && row.tab !== "applied") {
    label = `${row.questions} ${row.questions === 1 ? "Question" : "Questions"} to Write`;
    ink = "text-warning";
    glyph = <PencilLineIcon aria-hidden className="size-3.5 shrink-0" />;
  } else if (row.tab) {
    const status = TAB_STATUS[row.tab];
    label = status.label;
    ink = status.ink;
    glyph =
      row.tab === "filling" ? (
        // A spinning ring while it fills, drawn as Tailor's run loader is; still with reduced motion.
        <span
          aria-hidden="true"
          className="border-advanced/25 border-t-advanced size-3.5 shrink-0 animate-spin rounded-full border-2 motion-reduce:animate-none"
        />
      ) : (
        <status.Icon aria-hidden className="size-3.5 shrink-0" />
      );
  } else if (row.tabClosed) {
    // Not "Tab Closed · Reopen" (cut 2026-10-29 as layers of text): one item, the click reopens it.
    label = "Tab Closed, Not Submitted";
    ink = "text-warning";
    glyph = <WarningIcon aria-hidden className="size-3.5 shrink-0" />;
  } else if (row.group === "progress") {
    label = "Needs Your Input";
    ink = "text-warning";
    glyph = <WarningIcon aria-hidden className="size-3.5 shrink-0" />;
  } else {
    return null;
  }

  return (
    // A button, so the row's own click (it opens the job) leaves it alone (components/clickable-row.tsx).
    <button
      type="button"
      onClick={() => onAction(row)}
      // What "Needs Your Input" asks for: the extension says only that the
      // fill stopped, not at which field, so the label cannot name it.
      title={
        label === "Needs Your Input"
          ? "Auto Apply stopped at a field it can't fill. Open the application to finish it."
          : row.tab
            ? "Go to its tab"
            : "Open it again"
      }
      className={cn(
        "text-note focus-visible:ring-brand-ring inline-flex items-center gap-1.5 rounded-sm font-medium underline-offset-2 hover:underline focus-visible:ring-2 focus-visible:outline-none",
        ink,
      )}
    >
      {glyph}
      {label}
    </button>
  );
}

/** A status with nothing to open: a word and its glyph, as a button's look
 *  without the button. */
function PlainStatus({ Icon, label, ink }: { Icon: typeof CheckIcon; label: string; ink: string }) {
  return (
    <span className={cn("text-note inline-flex items-center gap-1.5 font-medium", ink)}>
      <Icon aria-hidden className="size-3.5 shrink-0" />
      {label}
    </span>
  );
}
