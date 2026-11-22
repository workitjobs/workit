import { StatTile } from "@/components/stat-tile";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { ScrapeHealth } from "@/lib/fill-health";

/**
 * Scrape Health's four numbers in one box (KAN-879), beside the status
 * card: boards ever read, and the window's new jobs, reads done and reads
 * failed. Each is WorkIt's own `StatTile` in its `plain` form, the company
 * Overview's row: a label on a hairline over the figure.
 *
 * A NUMBER HAS NO LINE OF WORDS UNDER IT. Each had one ("56% of all reads",
 * "43 open now", "of 5,043, ever"), and the user had them removed: they did
 * not help, and they read as written by a machine (2026-11-22). A number
 * that needs a second number is two labelled numbers, never a caption.
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
  className,
}: {
  /** The answer cut to the page's window. */
  data: ScrapeHealth;
  className?: string;
}) {
  const read = data.systems.reduce((sum, s) => sum + s.read, 0);
  const done = data.days.reduce((sum, d) => sum + d.done, 0);
  const failed = data.days.reduce((sum, d) => sum + d.failed, 0);
  const newJobs = data.days.reduce((sum, d) => sum + d.new_jobs, 0);

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
        <StatTile plain label="Boards Read" value={read} />
        <StatTile plain label="New Jobs Seen" value={newJobs} />
        <StatTile plain label="Reads Done" value={done} />
        <StatTile plain label="Reads Failed" value={failed} />
      </div>
    </Card>
  );
}
