import { Tip } from "@/components/ui/tip";
import { dayLabel as label, rangeOf } from "@/lib/scrape-status";

import type { AdminSection } from "./pages";
import { Panel } from "./panel";

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

/** One stacked part of a day's column: its name in the key and its fill. */
export type Series = { label: string; swatch: string };

/**
 * A count per day (UTC) for an admin page's window, as stacked columns
 * (KAN-879; shared by Scrape Health and Resume Reading since KAN-953): each
 * series stacked on the one before it, on one axis whose top follows the
 * tallest day in view, so it fits two or twenty thousand. Every day of the
 * window has a column's place, so a day with nothing is a gap. A day with a
 * count is a button: its numbers show in a tooltip on hover and on keyboard
 * focus, and its name says them to a screen reader. The figure's caption
 * sums the window. The page's period sets its days; it has no controls of
 * its own, and its header is the one place the days in view are written.
 *
 * A column has a 2px floor (`min-h-0.5`): 3 failed reads on a 5,000 axis
 * drew 0.13px, so a day with failures showed no red.
 */
export function DayColumns({
  section,
  dates,
  series,
  values,
  says,
  caption,
  className,
}: {
  section: AdminSection;
  /** The window's days, YYYY-MM-DD, oldest first. */
  dates: string[];
  /** The stack, bottom first. */
  series: readonly Series[];
  /** Each day's count per series, in `series` order; a day left out has none. */
  values: ReadonlyMap<string, readonly number[]>;
  /** A day's numbers in words, after its date: "12 done, 3 failed". */
  says: (counts: readonly number[]) => string;
  /** The window's sum in words, for a screen reader, before the days in view. */
  caption: string;
  className?: string;
}) {
  const none = series.map(() => 0);
  const days = dates.map((d) => values.get(d) ?? none);
  const sum = (counts: readonly number[]) => counts.reduce((total, n) => total + n, 0);
  const top = niceTop(Math.max(...days.map(sum)));
  const share = (n: number) => `${(n / top) * 100}%`;
  const range = rangeOf(dates);

  return (
    <Panel
      section={section}
      className={className}
      action={<span className="text-note text-ink-meta">{range} (UTC)</span>}
    >
      <figure className="flex h-full flex-col">
        <figcaption className="sr-only">
          {caption}, {range}.
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
                const day = days[i];
                if (sum(day) === 0) return <div key={date} className="flex-1" />;
                const name = `${label(date)}: ${says(day)}`;
                // The topmost part with a count has the column's rounded top.
                const topmost = day.findLastIndex((n) => n > 0);
                return (
                  <Tip key={date} label={name} side="top">
                    <button
                      type="button"
                      aria-label={name}
                      className="hover:bg-hover focus-visible:ring-brand-ring flex h-full min-w-0 flex-1 flex-col-reverse items-center justify-start gap-0.5 rounded-xs focus-visible:ring-2 focus-visible:outline-none"
                    >
                      {series.map(
                        (s, at) =>
                          day[at] > 0 && (
                            <span
                              key={s.label}
                              className={`${s.swatch} block min-h-0.5 w-full max-w-8 ${at === topmost ? "rounded-t-xs" : ""}`}
                              style={{ height: share(day[at]) }}
                            />
                          ),
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
          {series.map((s) => (
            <Key key={s.label} swatch={s.swatch}>
              {s.label}
            </Key>
          ))}
        </div>
      </figure>
    </Panel>
  );
}
