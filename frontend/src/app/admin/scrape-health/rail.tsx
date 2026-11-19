import type { ScrapeHealth } from "@/lib/fill-health";

import { Panel } from "../panel";
import { ClosableRail } from "./closable-rail";

const count = (n: number) => n.toLocaleString("en-US");

/** One count beside its name. */
function Row({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) {
  return (
    <li className="border-border-subtle text-body flex items-center justify-between gap-3 border-b px-5 py-3 last:border-b-0">
      <span className="text-ink-muted">{label}</span>
      <span
        className={
          alert
            ? "bg-danger-tint text-danger rounded-full px-2 py-0.5 font-medium tabular-nums"
            : "text-ink font-semibold tabular-nums"
        }
      >
        {value}
      </span>
    </li>
  );
}

/**
 * Scrape Health's right rail (KAN-879): the counts of boards and tasks now,
 * and the failing boards with their last error. The page's tiles and charts
 * hold the headline numbers; the rail is the detail an admin can close.
 */
export function ScrapeRail({ data }: { data: ScrapeHealth }) {
  const { boards } = data;
  return (
    <ClosableRail>
      <Panel title="Now" bodyClassName="p-0">
        <ul>
          <Row label="Boards" value={count(boards.boards)} />
          <Row label="Stale Boards" value={count(boards.stale)} alert={boards.stale > 0} />
          <Row label="Failing Boards" value={count(boards.failing)} alert={boards.failing > 0} />
          <Row label="Resting Boards" value={count(boards.resting)} />
          <Row label="Tasks Pending" value={count(boards.pending)} />
          <Row label="Tasks Claimed" value={count(boards.claimed)} />
          <Row label="Open Jobs" value={count(boards.open_jobs)} />
        </ul>
      </Panel>

      <Panel title="Failing Boards" bodyClassName="p-0">
        {data.failing.length === 0 ? (
          <p className="text-body text-ink-muted p-5">No board is failing.</p>
        ) : (
          <ul>
            {data.failing.map((b) => (
              <li
                key={`${b.ats}:${b.token}`}
                className="border-border-subtle flex items-start gap-3 border-b px-5 py-3.5 last:border-b-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-body text-ink font-medium">{b.company}</p>
                  <p className="text-label text-ink-meta font-normal break-all">
                    {b.ats}:{b.token}
                  </p>
                  {b.last_error && (
                    <p className="text-label text-danger mt-1 font-normal break-words">
                      {b.last_error}
                    </p>
                  )}
                </div>
                <span
                  className="bg-danger-tint text-danger text-label rounded-full px-2 py-0.5 whitespace-nowrap"
                  title="Failed reads in a row"
                >
                  {b.consecutive_failures} failed
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </ClosableRail>
  );
}
