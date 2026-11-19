import {
  BriefcaseIcon,
  CheckCircleIcon,
  HourglassIcon,
  WarningIcon,
} from "@phosphor-icons/react/ssr";
import type { ElementType } from "react";

import { cn } from "@/lib/cn";
import { percent, type ScrapeHealth } from "@/lib/fill-health";

const count = (n: number) => n.toLocaleString("en-US");

/** One headline number on a filled tile: white on a fill that holds 4.5:1. */
function Tile({
  value,
  label,
  note,
  icon: Icon,
  fill,
}: {
  value: string;
  label: string;
  note: string;
  icon: ElementType;
  fill: string;
}) {
  return (
    <div className={cn("rounded-card text-on-brand relative overflow-hidden p-5", fill)}>
      <p className="text-3xl font-bold tracking-tight tabular-nums">{value}</p>
      <p className="text-caption mt-1 uppercase">{label}</p>
      <p className="text-label mt-3 font-normal opacity-90">{note}</p>
      <Icon
        size={64}
        weight="fill"
        aria-hidden
        className="absolute top-1/2 right-4 -translate-y-1/2 opacity-20"
      />
    </div>
  );
}

/**
 * Scrape Health's four headline numbers (KAN-879): boards ever read, new
 * jobs seen and failed reads in the period, and the tasks waiting. Red is
 * the failure tile only.
 */
export function ScrapeTiles({ data, days }: { data: ScrapeHealth; days: number }) {
  const read = data.systems.reduce((sum, s) => sum + s.read, 0);
  const done = data.days.reduce((sum, d) => sum + d.done, 0);
  const failed = data.days.reduce((sum, d) => sum + d.failed, 0);
  const newJobs = data.days.reduce((sum, d) => sum + d.new_jobs, 0);
  const period = `Last ${days} ${days === 1 ? "day" : "days"}`;

  return (
    <div className="grid grid-cols-1 gap-4 @md:grid-cols-2 @3xl:grid-cols-4">
      <Tile
        value={count(read)}
        label="Boards Read"
        note={`of ${count(data.boards.boards)} boards`}
        icon={CheckCircleIcon}
        fill="bg-brand"
      />
      <Tile
        value={count(newJobs)}
        label="New Jobs Seen"
        note={period}
        icon={BriefcaseIcon}
        fill="bg-positive-ink"
      />
      <Tile
        value={count(data.boards.pending)}
        label="Tasks Pending"
        note={`${count(data.boards.claimed)} claimed`}
        icon={HourglassIcon}
        fill="bg-advanced"
      />
      <Tile
        value={count(failed)}
        label="Failed Reads"
        note={
          done + failed
            ? `${percent(failed / (done + failed))} of ${count(done + failed)} reads · ${period}`
            : period
        }
        icon={WarningIcon}
        fill="bg-danger"
      />
    </div>
  );
}
