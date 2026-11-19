import { CheckCircleIcon, WarningCircleIcon, WarningIcon } from "@phosphor-icons/react/ssr";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { ScrapeHealth } from "@/lib/fill-health";
import type { Status } from "@/lib/scrape-status";

const count = (n: number) => n.toLocaleString("en-US");
const when = (iso: string | null) =>
  iso ? `${new Date(iso).toISOString().slice(0, 16).replace("T", " ")} UTC` : "Never";

/** Each level's glyph and colours. The glyph and the title say the level, so it is never colour alone. */
const LEVELS = {
  red: { Icon: WarningIcon, chip: "bg-danger-tint text-danger", edge: "border-danger" },
  amber: { Icon: WarningCircleIcon, chip: "bg-warning-tint text-warning", edge: "border-warning" },
  green: {
    Icon: CheckCircleIcon,
    chip: "bg-positive-tint text-positive-ink",
    edge: "border-border-surface",
  },
} as const;

/** One fact under the status: its name over its value. */
function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-note text-ink-meta">{label}</dt>
      <dd className="text-body text-ink font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/**
 * Scrape Health's first card (KAN-879): the page's one answer, whether the
 * scrape is running, with the reason in a sentence and the counts now
 * under it. An admin reads this card and may stop there.
 */
export function StatusLine({ status, data }: { status: Status; data: ScrapeHealth }) {
  const { Icon, chip, edge } = LEVELS[status.level];
  const { boards } = data;
  return (
    <Card as="section" padding="lg" className={edge} aria-labelledby="scrape-status">
      <div className="flex items-start gap-4">
        <span
          className={cn("rounded-control flex size-10 shrink-0 items-center justify-center", chip)}
        >
          <Icon size={22} weight="fill" aria-hidden />
        </span>
        <div className="min-w-0">
          <h2 id="scrape-status" className="text-title text-ink">
            {status.title}
          </h2>
          <p className="text-body text-ink-muted mt-1 max-w-(--measure-prose)">
            {status.reason} These numbers describe the worker, which is not scheduled yet. The
            scheduled scrape last imported jobs at {when(data.last_import_at)}.
          </p>
        </div>
      </div>
      <dl className="border-border-subtle mt-5 grid grid-cols-2 gap-x-6 gap-y-4 border-t pt-4 @2xl/main:grid-cols-3 @5xl/main:grid-cols-6">
        <Fact label="Stale Boards" value={`${count(boards.stale)} of ${count(boards.boards)}`} />
        <Fact label="Failing Boards" value={count(boards.failing)} />
        <Fact label="Resting Boards" value={count(boards.resting)} />
        <Fact label="Tasks Pending" value={count(boards.pending)} />
        <Fact label="Tasks Claimed" value={count(boards.claimed)} />
        <Fact label="Oldest Pending Task" value={when(boards.oldest_pending_at)} />
      </dl>
    </Card>
  );
}
