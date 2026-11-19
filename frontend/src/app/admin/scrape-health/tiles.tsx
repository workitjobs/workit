import {
  BriefcaseIcon,
  CheckCircleIcon,
  HourglassIcon,
  WarningIcon,
} from "@phosphor-icons/react/ssr";

import { StatTile } from "@/components/stat-tile";
import { percent, type ScrapeHealth } from "@/lib/fill-health";

const count = (n: number) => n.toLocaleString("en-US");

/**
 * Scrape Health's four numbers (KAN-879), each WorkIt's own `StatTile`, as
 * Home's are: a white tile, the figure in ink, and colour only in the
 * glyph's chip. Failed Reads takes the red chip only while it is above
 * zero. They were four filled tiles (violet, green, blue, red), which a
 * design review found ranked by colour, not by size and weight, and made
 * three calm numbers as loud as the failure.
 */
export function ScrapeTiles({ data, open }: { data: ScrapeHealth; open: number }) {
  const read = data.systems.reduce((sum, s) => sum + s.read, 0);
  const done = data.days.reduce((sum, d) => sum + d.done, 0);
  const failed = data.days.reduce((sum, d) => sum + d.failed, 0);
  const newJobs = data.days.reduce((sum, d) => sum + d.new_jobs, 0);

  return (
    <div className="grid grid-cols-2 gap-4 @4xl/main:grid-cols-4">
      <StatTile
        label="Boards Read"
        Icon={CheckCircleIcon}
        tone="bg-kpi-applied-chip text-kpi-applied"
        value={read}
        note={`of ${count(data.boards.boards)} boards, ever`}
      />
      <StatTile
        label="New Jobs Seen"
        Icon={BriefcaseIcon}
        tone="bg-kpi-match-chip text-kpi-match"
        value={newJobs}
        note={`${count(open)} open now`}
      />
      <StatTile
        label="Reads Done"
        Icon={HourglassIcon}
        value={done}
        note={done + failed ? `${percent(done / (done + failed))} of all reads` : "No reads"}
      />
      <StatTile
        label="Reads Failed"
        Icon={WarningIcon}
        tone={failed > 0 ? "bg-danger-tint text-danger" : undefined}
        value={failed}
        note={done + failed ? `${percent(failed / (done + failed))} of all reads` : "No reads"}
      />
    </div>
  );
}
