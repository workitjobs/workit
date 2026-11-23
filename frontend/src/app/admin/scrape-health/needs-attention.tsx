import type { ScrapeHealth } from "@/lib/fill-health";
import { dayLabel, HISTORY, systemName } from "@/lib/scrape-status";

import { SCRAPE_SECTIONS } from "../pages";
import { Panel } from "../panel";

const count = (n: number) => n.toLocaleString("en-US");
const SUBHEAD = "text-label text-ink-meta bg-well border-border-subtle border-b px-5 py-2";
const ROW = "border-border-subtle border-b px-5 py-3 last:border-b-0";
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
 * The lists scroll inside the box, so a long one does not push the page's
 * tables down.
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
      bodyClassName="p-0 max-h-[34rem] overflow-y-auto"
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
          <ul>
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
                {e.error && (
                  <details className="mt-1">
                    <summary className="text-note text-ink-muted cursor-pointer [overflow-wrap:anywhere]">
                      Newest: {e.company} ({systemName(e.ats)})
                    </summary>
                    <p className="text-note text-danger mt-1 [overflow-wrap:anywhere]">{e.error}</p>
                  </details>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {failing.length > 0 && (
        <>
          <h3 className={`${SUBHEAD} ${errors.length > 0 ? "border-t" : ""}`}>Failing Boards</h3>
          <ul>
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
          </ul>
        </>
      )}
    </Panel>
  );
}
