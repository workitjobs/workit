import { cn } from "@/lib/cn";
import { type ReadingHealth, statusOf } from "@/lib/resume-reading";
import { datesOf, type Window } from "@/lib/scrape-status";

import { ADMIN_FRAME } from "../panel";
import { WindowControls } from "../scrape-health/window-controls";
import { Accuracy, Models, Now, PerDay, Reasons } from "./parts";
import { ReadingsTable } from "./readings-table";

/**
 * The Resume Reading page drawn from one answer of the API (KAN-953), apart
 * from the page's read so it can be drawn from any answer.
 *
 * Four groups, 32px apart, with 16px inside a group: the space between
 * groups is larger than the space inside one, so the groups read as groups.
 * Now (the answer and four numbers, on the ground), the trend (the chart
 * beside the reasons), quality and cost (accuracy beside the models, the
 * split mirrored so the page does not repeat one shape), and the log.
 */
export function ReadingView({ health, window }: { health: ReadingHealth; window: Window }) {
  /** The newest day the page shows: the day (UTC) the API's answer was read. */
  const today = health.read_at.slice(0, 10);
  const dates = datesOf(window, today);

  return (
    <main className={cn("@container/main", ADMIN_FRAME)}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-heading text-ink">Resume Reading</h1>
          <p className="text-note text-ink-meta mt-1">
            Who read each uploaded resume. Counts only, never resume text.
          </p>
        </div>
        <WindowControls window={window} path="/admin/resume-reading" />
      </div>

      <div className="mt-8 flex flex-col gap-8">
        <Now status={statusOf(health)} health={health} />
        {/* `*:min-w-0`: a grid item is at least as wide as its content, so a table pushed its card past a phone's edge. */}
        <div className="grid gap-4 *:min-w-0 @4xl/main:grid-cols-3">
          <PerDay days={health.days} dates={dates} className="@4xl/main:col-span-2" />
          <Reasons reasons={health.reasons} />
        </div>
        <div className="grid gap-4 *:min-w-0 @4xl/main:grid-cols-3">
          <Accuracy run={health.accuracy} />
          <Models models={health.models} className="@4xl/main:col-span-2" />
        </div>
        <ReadingsTable rows={health.recent} />
      </div>
    </main>
  );
}
