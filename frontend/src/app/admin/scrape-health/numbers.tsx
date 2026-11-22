import { StatTile } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { percent, type ScrapeHealth } from "@/lib/fill-health";

const count = (n: number) => n.toLocaleString("en-US");

/**
 * Scrape Health's four numbers in one box (KAN-879), beside the status
 * card: boards ever read, and the window's new jobs, reads done and reads
 * failed. Each is WorkIt's own `StatTile` in its `plain` form, the company
 * Overview's row: a label on a hairline over the figure and one line.
 * Colour marks a state only, so Reads Failed takes a red pill while it is
 * above zero, with its share in words.
 *
 * They were four tiles in a row of their own, which the user found took a
 * whole row for four numbers (2026-11-22). Before that they were four
 * filled tiles (violet, green, blue, red), which a design review found
 * ranked by colour, not by size and weight.
 *
 * The box is its own container: two numbers a row where it stands beside
 * the status card, and four where it has the page's width.
 */
export function ScrapeNumbers({
  data,
  open,
  className,
}: {
  /** The answer cut to the page's window. */
  data: ScrapeHealth;
  /** The scraped jobs open now. */
  open: number;
  className?: string;
}) {
  const read = data.systems.reduce((sum, s) => sum + s.read, 0);
  const done = data.days.reduce((sum, d) => sum + d.done, 0);
  const failed = data.days.reduce((sum, d) => sum + d.failed, 0);
  const newJobs = data.days.reduce((sum, d) => sum + d.new_jobs, 0);
  const reads = done + failed;
  const share = (n: number) => (reads ? `${percent(n / reads)} of all reads` : "No reads");

  return (
    <Card
      as="section"
      tone="tile"
      padding="lg"
      aria-label="Numbers"
      // Centred in the height the status card beside it sets.
      className={cn("@container/numbers flex flex-col justify-center", className)}
    >
      <div className="grid grid-cols-2 gap-x-5 gap-y-4 @xl/numbers:grid-cols-4">
        <StatTile
          plain
          label="Boards Read"
          value={read}
          note={`of ${count(data.boards.boards)}, ever`}
        />
        <StatTile plain label="New Jobs Seen" value={newJobs} note={`${count(open)} open now`} />
        <StatTile plain label="Reads Done" value={done} note={share(done)} />
        <StatTile
          plain
          label="Reads Failed"
          value={failed}
          note={
            failed > 0 ? (
              <Badge tone="danger" pill>
                {share(failed)}
              </Badge>
            ) : (
              share(failed)
            )
          }
        />
      </div>
    </Card>
  );
}
