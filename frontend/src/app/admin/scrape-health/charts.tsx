import type { ScrapeHealth } from "@/lib/fill-health";

const count = (n: number) => n.toLocaleString("en-US");

/** The axis top for `max`: the next 1, 2 or 5 times a power of ten, so the half line is a round number. */
function niceTop(max: number): number {
  if (max <= 2) return 2;
  const power = 10 ** Math.floor(Math.log10(max));
  const top = [1, 2, 5, 10].find((step) => step * power >= max) ?? 10;
  return top * power;
}

/** The last `days` days (UTC) as ISO dates, oldest first, ending today. */
function lastDays(days: number): string[] {
  const today = Date.now();
  return Array.from({ length: days }, (_, i) =>
    new Date(today - (days - 1 - i) * 86_400_000).toISOString().slice(0, 10),
  );
}

function Key({ swatch, children }: { swatch: string; children: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`size-2.5 rounded-sm ${swatch}`} aria-hidden />
      {children}
    </span>
  );
}

/**
 * Board reads per day (UTC) for the period, as stacked columns: done in
 * brand under failed in red, on one axis. Every day of the period has a
 * column's place, so a day with no reads shows as a gap. Each column's
 * tooltip gives its numbers, and the Board Reads table below is its table
 * view.
 */
export function DailyReads({ rows, days }: { rows: ScrapeHealth["days"]; days: number }) {
  const byDay = new Map<string, { done: number; failed: number }>();
  for (const r of rows) {
    const day = byDay.get(r.day) ?? { done: 0, failed: 0 };
    byDay.set(r.day, { done: day.done + r.done, failed: day.failed + r.failed });
  }
  const dates = lastDays(days);
  const top = niceTop(
    Math.max(...dates.map((d) => (byDay.get(d)?.done ?? 0) + (byDay.get(d)?.failed ?? 0))),
  );
  const share = (n: number) => `${(n / top) * 100}%`;

  return (
    <figure>
      <div className="flex gap-3">
        <div className="text-label text-ink-meta flex h-52 flex-col justify-between text-right font-normal tabular-nums">
          <span className="-translate-y-1/2">{count(top)}</span>
          <span>{count(top / 2)}</span>
          <span className="translate-y-1/2">0</span>
        </div>
        <div className="relative h-52 min-w-0 flex-1">
          <div className="border-border-subtle absolute inset-x-0 top-0 border-t" />
          <div className="border-border-subtle absolute inset-x-0 top-1/2 border-t" />
          <div className="border-border-surface absolute inset-x-0 bottom-0 border-t" />
          <div className="absolute inset-0 flex items-end gap-0.5">
            {dates.map((date) => {
              const { done, failed } = byDay.get(date) ?? { done: 0, failed: 0 };
              return (
                <div
                  key={date}
                  title={`${date}: ${count(done)} done, ${count(failed)} failed`}
                  className="hover:bg-hover flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-0.5"
                >
                  {failed > 0 && (
                    <div
                      className="bg-danger w-full max-w-8 rounded-t-sm"
                      style={{ height: share(failed) }}
                    />
                  )}
                  {done > 0 && (
                    <div
                      className={`bg-brand w-full max-w-8 ${failed > 0 ? "" : "rounded-t-sm"}`}
                      style={{ height: share(done) }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="text-label text-ink-meta mt-2 flex justify-between pl-10 font-normal tabular-nums">
        <span>{dates[0]}</span>
        {days > 2 && <span>{dates[Math.floor(days / 2)]}</span>}
        {days > 1 && <span>{dates[days - 1]}</span>}
      </div>
      <figcaption className="text-label text-ink-muted mt-4 flex flex-wrap justify-center gap-5 font-normal">
        <Key swatch="bg-brand">Done</Key>
        <Key swatch="bg-danger">Failed</Key>
      </figcaption>
    </figure>
  );
}

/**
 * The catalog's boards per hiring system, most first: each bar's length is
 * the system's boards against the largest system's, and its dark part the
 * boards ever read. A row's figure says both, so no part is read by colour
 * alone. Bars, not a donut: 13 systems are compared, and a donut's slices
 * cannot be.
 */
export function SystemBars({ systems }: { systems: ScrapeHealth["systems"] }) {
  const most = Math.max(...systems.map((s) => s.boards), 1);
  return (
    <div>
      <ul className="space-y-3">
        {systems.map((s) => (
          <li key={s.ats}>
            <div className="text-body flex items-baseline justify-between gap-3">
              <span className="text-ink font-medium capitalize">{s.ats}</span>
              <span className="text-ink-meta tabular-nums">
                <span className="text-ink font-medium">{count(s.read)}</span> / {count(s.boards)}
              </span>
            </div>
            <div
              className="bg-brand-pale mt-1.5 h-2 overflow-hidden rounded-r-sm"
              style={{ width: `${Math.max((s.boards / most) * 100, 1)}%` }}
              title={`${count(s.read)} of ${count(s.boards)} boards read`}
            >
              <div className="bg-brand h-full" style={{ width: `${(s.read / s.boards) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-label text-ink-muted mt-5 flex flex-wrap justify-center gap-5 font-normal">
        <Key swatch="bg-brand">Read</Key>
        <Key swatch="bg-brand-pale">Not Read Yet</Key>
      </p>
    </div>
  );
}
