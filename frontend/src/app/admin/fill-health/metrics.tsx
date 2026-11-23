import { StatTile } from "@/components/stat-tile";
import { fillTotals, type FillHealthRow } from "@/lib/fill-health";
import { systemName } from "@/lib/scrape-status";

import { FILL_SECTIONS, FIRST_SECTION_TARGET } from "../pages";
import { Panel } from "../panel";

/**
 * Fill Health's numbers (KAN-879): the fills in the page's window, all of
 * them first, then each job system's, most first. Every number is a sum of
 * the rows' fills, so it is exact. The page's two rates are left out on
 * purpose: a rate for the whole window would need the pages and fields
 * behind each row, which the API does not answer, and a mean of rates is a
 * different number. A number has no line of words under it
 * (`scrape-health/numbers.tsx`).
 */
export function FillMetrics({ rows }: { rows: FillHealthRow[] }) {
  const { fills, systems } = fillTotals(rows);
  return (
    <Panel section={FILL_SECTIONS.metrics} className={FIRST_SECTION_TARGET}>
      <div className="grid grid-cols-2 gap-x-5 gap-y-4 @2xl/main:grid-cols-4 @5xl/main:grid-cols-6">
        <StatTile plain label="Total Fills" value={fills} />
        {systems.map((s) => (
          <StatTile key={s.job_system} plain label={systemName(s.job_system)} value={s.fills} />
        ))}
      </div>
    </Panel>
  );
}
