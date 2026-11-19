import { Card } from "@/components/ui/card";

import { ClosableRail } from "./closable-rail";
import { percent, type ScrapeHealth } from "@/lib/fill-health";

/** A rail section's small capital heading. */
function RailHeading({ children, note }: { children: string; note?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <h3 className="text-caption text-ink uppercase">{children}</h3>
      {note && <span className="text-label text-ink-meta font-normal">{note}</span>}
    </div>
  );
}

const R = 52;
const AROUND = 2 * Math.PI * R;
/** The gauge is three quarters of a circle, open at the foot. */
const SWEEP = 0.75 * AROUND;

/** A three-quarter ring filled to `share`, with its number in the middle. */
function Gauge({ share, value, label }: { share: number; value: string; label: string }) {
  // A share above zero still shows: at least 1.5% of the ring.
  const filled = share > 0 ? Math.max(share, 0.015) * SWEEP : 0;
  return (
    <div className="relative mx-auto mt-4 w-44">
      <svg viewBox="0 0 120 120" aria-hidden className="block w-full rotate-[135deg]">
        <circle
          cx={60}
          cy={60}
          r={R}
          fill="none"
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${SWEEP} ${AROUND}`}
          className="stroke-brand-tint"
        />
        <circle
          cx={60}
          cy={60}
          r={R}
          fill="none"
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${AROUND}`}
          className="stroke-brand"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-ink text-2xl font-semibold tabular-nums">{value}</span>
        <span className="text-label text-ink-meta font-normal">{label}</span>
      </div>
    </div>
  );
}

/** One number over its label. */
function Stat({ value, label }: { value: string | number; label: string }) {
  return (
    <div>
      <dd className="text-ink text-lg font-semibold tabular-nums">{value}</dd>
      <dt className="text-label text-ink-meta font-normal">{label}</dt>
    </div>
  );
}

/**
 * Scrape Health's right rail (KAN-879): the share of boards ever read as a
 * gauge, the period's reads done against failed as one bar, the counts of
 * boards and tasks now, and the failing boards with their last error.
 */
export function ScrapeRail({ data, days }: { data: ScrapeHealth; days: number }) {
  const { boards } = data;
  const read = data.systems.reduce((sum, s) => sum + s.read, 0);
  const done = data.days.reduce((sum, d) => sum + d.done, 0);
  const failed = data.days.reduce((sum, d) => sum + d.failed, 0);
  const newJobs = data.days.reduce((sum, d) => sum + d.new_jobs, 0);
  const reads = done + failed;
  const period = `Last ${days} ${days === 1 ? "day" : "days"}`;

  return (
    <ClosableRail>
      <Card as="section" padding="lg">
        <RailHeading>Boards Read</RailHeading>
        <Gauge
          share={boards.boards ? read / boards.boards : 0}
          value={read.toLocaleString("en-US")}
          label={`of ${boards.boards.toLocaleString("en-US")} boards`}
        />
        <dl className="mt-2 grid grid-cols-2 gap-4">
          <Stat value={newJobs.toLocaleString("en-US")} label="New jobs seen" />
          <Stat value={boards.open_jobs.toLocaleString("en-US")} label="Open jobs" />
        </dl>
      </Card>

      <Card as="section" padding="lg">
        <RailHeading note={period}>Board Reads</RailHeading>
        {reads === 0 ? (
          <p className="text-body text-ink-muted mt-3">No board reads in this period.</p>
        ) : (
          <>
            <div className="mt-4 flex h-1.5 gap-0.5 overflow-hidden rounded-full">
              <span className="bg-brand" style={{ flexGrow: done }} />
              <span className="bg-danger" style={{ flexGrow: failed }} />
            </div>
            <ul className="text-body mt-3 space-y-2">
              <li className="flex items-center gap-2">
                <span className="bg-brand size-1.5" aria-hidden />
                <span className="text-ink flex-1">Done</span>
                <span className="text-ink-meta tabular-nums">{done}</span>
                <span className="text-ink w-10 text-right font-medium tabular-nums">
                  {percent(done / reads)}
                </span>
              </li>
              <li className="flex items-center gap-2">
                <span className="bg-danger size-1.5" aria-hidden />
                <span className="text-ink flex-1">Failed</span>
                <span className="text-ink-meta tabular-nums">{failed}</span>
                <span className="text-ink w-10 text-right font-medium tabular-nums">
                  {percent(failed / reads)}
                </span>
              </li>
            </ul>
          </>
        )}
      </Card>

      <Card as="section" padding="lg">
        <RailHeading note="Now">Overview</RailHeading>
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-5">
          <Stat value={boards.stale.toLocaleString("en-US")} label="Stale boards" />
          <Stat value={boards.failing} label="Failing boards" />
          <Stat value={boards.resting} label="Resting boards" />
          <Stat value={boards.pending.toLocaleString("en-US")} label="Tasks pending" />
          <Stat value={boards.claimed} label="Tasks claimed" />
        </dl>
      </Card>

      <Card as="section" padding="lg">
        <RailHeading>Failing Boards</RailHeading>
        {data.failing.length === 0 ? (
          <p className="text-body text-ink-muted mt-3">No board is failing.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {data.failing.map((b) => (
              <li key={`${b.ats}:${b.token}`} className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-body text-ink font-medium">{b.company}</p>
                  <p className="text-label text-ink-meta font-normal break-all">
                    {b.ats}:{b.token}
                  </p>
                  {b.last_error && (
                    <p className="text-label text-danger font-normal break-words">{b.last_error}</p>
                  )}
                </div>
                <span
                  className="text-body text-ink font-medium tabular-nums"
                  title="Failed reads in a row"
                >
                  {b.consecutive_failures}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </ClosableRail>
  );
}
