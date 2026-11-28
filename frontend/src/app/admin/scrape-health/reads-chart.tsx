import type { ScrapeHealth } from "@/lib/fill-health";

import { DayColumns, type Series } from "../day-columns";
import { count } from "../format";
import { SCRAPE_SECTIONS } from "../pages";

/** Done in brand under failed in red. */
const SERIES: readonly Series[] = [
  { label: "Done", swatch: "bg-brand" },
  { label: "Failed", swatch: "bg-danger" },
];

/**
 * Board reads per day (UTC) for the page's window (KAN-879), on the admin
 * pages' shared chart (`../day-columns.tsx`): done in brand under failed in
 * red. The Board Reads table is the table view.
 */
export function ReadsChart({
  rows,
  dates,
  className,
}: {
  rows: ScrapeHealth["days"];
  /** The window's days, YYYY-MM-DD, oldest first. */
  dates: string[];
  className?: string;
}) {
  const byDay = new Map<string, [number, number]>();
  for (const r of rows) {
    const [done, failed] = byDay.get(r.day) ?? [0, 0];
    byDay.set(r.day, [done + r.done, failed + r.failed]);
  }
  const done = [...byDay.values()].reduce((sum, d) => sum + d[0], 0);
  const failed = [...byDay.values()].reduce((sum, d) => sum + d[1], 0);

  return (
    <DayColumns
      section={SCRAPE_SECTIONS.perDay}
      dates={dates}
      series={SERIES}
      values={byDay}
      says={([d, f]) => `${count(d)} done, ${count(f)} failed`}
      caption={`${count(done)} board reads done and ${count(failed)} failed`}
      className={className}
    />
  );
}
