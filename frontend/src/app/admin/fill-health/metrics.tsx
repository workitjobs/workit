import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { fillTotals, type FillHealthRow } from "@/lib/fill-health";
import { systemName } from "@/lib/scrape-status";

import { FILL_SECTIONS, FIRST_SECTION_TARGET } from "../pages";

const count = (n: number) => n.toLocaleString("en-US");

/**
 * Fill Health's numbers (KAN-879), in one line: the window's fills, then
 * each job system's as a chip, most first. Every number is a sum of the
 * rows' fills, so it is exact. The page's two rates are left out on
 * purpose: a rate for the whole window would need the pages and fields
 * behind each row, which the API does not answer, and a mean of rates is a
 * different number.
 *
 * It was a titled card with a large tile per job system, seven tiles over
 * two rows for seven small numbers, and the user asked for it far smaller
 * (2026-11-23). The total is the one figure; a job system's share is a
 * detail, so it is a chip. The card has no title row: "Total Fills" names
 * it, and the section's name is its label for the sidebar's link.
 */
export function FillMetrics({ rows }: { rows: FillHealthRow[] }) {
  const { fills, systems } = fillTotals(rows);
  return (
    <Card
      as="section"
      tone="tile"
      padding="none"
      id={FILL_SECTIONS.metrics.id}
      aria-label={FILL_SECTIONS.metrics.label}
      className={cn("flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4", FIRST_SECTION_TARGET)}
    >
      <p className="flex items-baseline gap-2">
        <span className="text-title text-ink tabular-nums">{count(fills)}</span>
        <span className="text-body text-ink-muted">Total Fills</span>
      </p>
      {systems.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {systems.map((s) => (
            <li
              key={s.job_system}
              className="bg-well text-note text-ink-muted rounded-full px-2.5 py-1 whitespace-nowrap"
            >
              {systemName(s.job_system)}{" "}
              <span className="text-ink font-medium tabular-nums">{count(s.fills)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
