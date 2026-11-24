import type { ReactNode } from "react";

import type { ScrapeHealth } from "@/lib/fill-health";
import { dayLabel, HISTORY, systemName } from "@/lib/scrape-status";

import { count } from "../format";
import { SCRAPE_SECTIONS } from "../pages";
import { Panel } from "../panel";

const SUBHEAD = "text-label text-ink-meta bg-well border-border-subtle border-b px-5 py-2";
const ROW = "border-border-subtle border-b px-5 py-3 last:border-b-0";
/** The rows a list shows before See More. */
const SHOWN = 5;
const PILL = "bg-danger-tint text-danger text-note rounded-full px-2 py-0.5 whitespace-nowrap";

/**
 * What an admin acts on (KAN-879), in two lists.
 *
 * FAILED READS BY REASON comes first: one line per reason (the error's text
 * before its first ": "), with the boards it failed and its newest read's
 * whole error behind a disclosure. It holds boards the list under it lacks:
 * a failed publish does not count as a board failure, so the page once
 * showed 2 failing boards while 90 reads had failed, 88 for one cause
 * (2026-11-15). It also folds the boards that fail by design (robots.txt,
 * oversized) into a line each, where they would fill the 25 rows below.
 * It covers every day the API answers (`HISTORY`), not the page's window:
 * the page cuts the days itself, and a group cannot be cut that way.
 *
 * FAILING BOARDS is each board with failed reads in a row, most first, with
 * its last error. Its count is the API's total, since the list stops at 25.
 *
 * Each list shows its first `SHOWN` rows, with the rest behind See More: a
 * list in a tile on a page never scrolls inside it (docs/design.md,
 * KAN-828), since a scroll box takes the mouse wheel from the page.
 */
export function NeedsAttention({
  failing,
  failingTotal,
  errors,
}: {
  failing: ScrapeHealth["failing"];
  /** Every failing board, where `failing` holds 25 at most. */
  failingTotal: number;
  errors: ScrapeHealth["errors"];
}) {
  const empty = failing.length === 0 && errors.length === 0;
  return (
    <Panel
      section={SCRAPE_SECTIONS.attention}
      bodyClassName="p-0"
      action={
        failingTotal > 0 && (
          <span className="text-note text-ink-meta">
            {failing.length < failingTotal
              ? `${count(failing.length)} of ${count(failingTotal)} failing boards`
              : `${count(failingTotal)} failing ${failingTotal === 1 ? "board" : "boards"}`}
          </span>
        )
      }
    >
      {empty && (
        <p className="text-body text-ink-muted p-5">
          No read failed in the last {HISTORY} days, and no board is failing.
        </p>
      )}

      {errors.length > 0 && (
        <>
          <h3 className={SUBHEAD}>Failed Reads by Reason · Last {HISTORY} Days</h3>
          <Rows>
            {errors.map((e) => (
              <li key={e.reason} className={ROW}>
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-body text-ink font-medium [overflow-wrap:anywhere]">
                      {e.reason || "No Error Text"}
                    </p>
                    <p className="text-note text-ink-meta tabular-nums">
                      {count(e.reads)} {e.reads === 1 ? "read" : "reads"} · last{" "}
                      {dayLabel(e.last_at.slice(0, 10))}
                    </p>
                  </div>
                  <span className={PILL}>
                    {count(e.boards)} {e.boards === 1 ? "board" : "boards"}
                  </span>
                </div>
                {/* An error with no detail ("robots.txt") is its reason: nothing to open. */}
                {e.error && e.error !== e.reason ? (
                  <details className="mt-1">
                    <summary className="text-note text-ink-muted cursor-pointer [overflow-wrap:anywhere]">
                      Newest: {e.company} ({systemName(e.ats)})
                    </summary>
                    <p className="text-note text-danger mt-1 [overflow-wrap:anywhere]">{e.error}</p>
                  </details>
                ) : (
                  <p className="text-note text-ink-muted mt-1 [overflow-wrap:anywhere]">
                    Newest: {e.company} ({systemName(e.ats)})
                  </p>
                )}
              </li>
            ))}
          </Rows>
        </>
      )}

      {failing.length > 0 && (
        <>
          <h3 className={`${SUBHEAD} ${errors.length > 0 ? "border-t" : ""}`}>Failing Boards</h3>
          <Rows>
            {failing.map((b) => (
              <li key={`${b.ats}:${b.token}`} className={`${ROW} flex items-start gap-3`}>
                <div className="min-w-0 flex-1">
                  <p className="text-body text-ink font-medium">{b.company}</p>
                  <p className="text-note text-ink-meta [overflow-wrap:anywhere]">
                    {systemName(b.ats)} · {b.token}
                  </p>
                  {b.last_error && (
                    <p className="text-note text-danger mt-1 [overflow-wrap:anywhere]">
                      {b.last_error}
                    </p>
                  )}
                </div>
                <span className={PILL}>{b.consecutive_failures} failed</span>
              </li>
            ))}
          </Rows>
        </>
      )}
    </Panel>
  );
}

/** A list's first rows, then the rest behind a native disclosure, so it needs no script. */
function Rows({ children }: { children: ReactNode[] }) {
  const rest = children.slice(SHOWN);
  return (
    <>
      <ul>{children.slice(0, SHOWN)}</ul>
      {rest.length > 0 && (
        <details className="border-border-subtle group border-t">
          <summary className="text-label text-brand-ink hover:bg-hover cursor-pointer px-5 py-3">
            {/* The summary stays when open, so the keyboard keeps its place and can close the list. */}
            <span className="group-open:hidden">See {count(rest.length)} More</span>
            <span className="hidden group-open:inline">See Fewer</span>
          </summary>
          <ul>{rest}</ul>
        </details>
      )}
    </>
  );
}
