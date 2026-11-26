import { Tip } from "@/components/ui/tip";
import type { ScrapeHealth } from "@/lib/fill-health";
import { dayLabel as label, rangeOf } from "@/lib/scrape-status";

import { count } from "../format";
import { SCRAPE_SECTIONS } from "../pages";
import { Panel } from "../panel";

/** An axis number, short once it is large: 1.5K, 20K. */
const short = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

/** The axis top for `max`: the next 1, 2 or 5 times a power of ten, so the half line is a round number. */
function niceTop(max: number): number {
  if (max <= 2) return 2;
  const power = 10 ** Math.floor(Math.log10(max));
  const top = [1, 2, 5, 10].find((step) => step * power >= max) ?? 10;
  return top * power;
}

export function Key({ swatch, children }: { swatch: string; children: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`size-2.5 rounded-xs ${swatch}`} aria-hidden />
      {children}
    </span>
  );
}

/**
 * Board reads per day (UTC) for the page's window, as stacked columns
 * (KAN-879): done in brand under failed in red, on one axis whose top
 * follows the tallest day in view, so it fits two reads or twenty
 * thousand. Every day of the window has a column's place, so a day with no
 * reads is a gap. A day with reads is a button: its numbers show in a
 * tooltip on hover and on keyboard focus, and its name says them to a
 * screen reader. The figure's caption sums the window, and the Board Reads
 * table is the table view. The page's period and arrows move it; it has no
 * controls of its own.
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
  const byDay = new Map<string, { done: number; failed: number }>();
  for (const r of rows) {
    const day = byDay.get(r.day) ?? { done: 0, failed: 0 };
    byDay.set(r.day, { done: day.done + r.done, failed: day.failed + r.failed });
  }
  const totals = dates.map((d) => byDay.get(d) ?? { done: 0, failed: 0 });
  const done = totals.reduce((sum, t) => sum + t.done, 0);
  const failed = totals.reduce((sum, t) => sum + t.failed, 0);
  const top = niceTop(Math.max(...totals.map((t) => t.done + t.failed)));
  const share = (n: number) => `${(n / top) * 100}%`;
  const range = rangeOf(dates);

  return (
    <Panel
      section={SCRAPE_SECTIONS.perDay}
      className={className}
      action={<span className="text-note text-ink-meta">{range} (UTC)</span>}
    >
      <figure className="flex h-full flex-col">
        <figcaption className="sr-only">
          {count(done)} board reads done and {count(failed)} failed, {range}.
        </figcaption>
        <div className="flex min-h-56 flex-1 gap-3">
          <div
            className="text-note text-ink-meta flex w-10 flex-col justify-between text-right tabular-nums"
            aria-hidden
          >
            <span className="-translate-y-1/2">{short.format(top)}</span>
            <span>{short.format(top / 2)}</span>
            <span className="translate-y-1/2">0</span>
          </div>
          <div className="relative min-w-0 flex-1">
            <div className="border-border-subtle absolute inset-x-0 top-0 border-t" />
            <div className="border-border-subtle absolute inset-x-0 top-1/2 border-t" />
            <div className="border-border-control absolute inset-x-0 bottom-0 border-t" />
            <div className="absolute inset-0 flex items-end gap-0.5">
              {dates.map((date, i) => {
                const day = totals[i];
                if (day.done + day.failed === 0) return <div key={date} className="flex-1" />;
                const says = `${label(date)}: ${count(day.done)} done, ${count(day.failed)} failed`;
                return (
                  <Tip key={date} label={says} side="top">
                    <button
                      type="button"
                      aria-label={says}
                      className="hover:bg-hover focus-visible:ring-brand-ring flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-0.5 rounded-xs focus-visible:ring-2 focus-visible:outline-none"
                    >
                      {day.failed > 0 && (
                        <span
                          className="bg-danger block min-h-0.5 w-full max-w-8 rounded-t-xs"
                          style={{ height: share(day.failed) }}
                        />
                      )}
                      {day.done > 0 && (
                        <span
                          className={`bg-brand block min-h-0.5 w-full max-w-8 ${day.failed > 0 ? "" : "rounded-t-xs"}`}
                          style={{ height: share(day.done) }}
                        />
                      )}
                    </button>
                  </Tip>
                );
              })}
            </div>
          </div>
        </div>
        <div
          className="text-note text-ink-meta mt-2 flex justify-between pl-13 tabular-nums"
          aria-hidden
        >
          <span>{label(dates[0])}</span>
          <span>{label(dates[Math.floor(dates.length / 2)])}</span>
          <span>{label(dates[dates.length - 1])}</span>
        </div>
        <div className="text-note text-ink-muted mt-4 flex flex-wrap justify-center gap-5">
          <Key swatch="bg-brand">Done</Key>
          <Key swatch="bg-danger">Failed</Key>
        </div>
      </figure>
    </Panel>
  );
}
