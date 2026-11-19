"use client";

import {
  CaretLeftIcon,
  CaretRightIcon,
  MagnifyingGlassMinusIcon,
  MagnifyingGlassPlusIcon,
} from "@phosphor-icons/react/ssr";
import { type ReactNode, useState } from "react";

import { HISTORY, type ScrapeHealth } from "@/lib/fill-health";

import { Panel } from "../panel";

const DAY = 86_400_000;
/** The days the chart can show at once, from most zoomed in to most zoomed out. */
const SPANS = [7, 14, 30, 90] as const;

const STEPS = { week: 7, month: 30 } as const;
type Step = keyof typeof STEPS;

const count = (n: number) => n.toLocaleString("en-US");
/** An axis number, short once it is large: 1.5K, 20K. */
const short = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const dayName = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

/** The axis top for `max`: the next 1, 2 or 5 times a power of ten, so the half line is a round number. */
function niceTop(max: number): number {
  if (max <= 2) return 2;
  const power = 10 ** Math.floor(Math.log10(max));
  const top = [1, 2, 5, 10].find((step) => step * power >= max) ?? 10;
  return top * power;
}

const BUTTON =
  "border-border-surface bg-panel text-ink hover:border-ink-meta focus-visible:ring-brand-ring rounded-control flex size-8 items-center justify-center border focus-visible:ring-2 focus-visible:outline-none disabled:opacity-40 disabled:hover:border-border-surface";

function IconButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={BUTTON}
    >
      {children}
    </button>
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
 * Board reads per day (UTC) as stacked columns (KAN-879): done in brand
 * under failed in red, on one axis whose top follows the tallest day in
 * view, so it fits two reads or twenty thousand. The page hands it the last
 * HISTORY days once; zoom picks how many days show (SPANS) and the arrows
 * move the window a week or a month at a time, all in the browser. Every
 * day in view has a column's place, so a day with no reads is a gap. Each
 * column's tooltip gives its numbers, and the Board Reads table is its
 * table view.
 *
 * `today` is the server's date, so the server and the browser draw the same
 * days.
 */
export function DailyReads({
  rows,
  today,
  days,
}: {
  rows: ScrapeHealth["days"];
  /** The newest day, YYYY-MM-DD (UTC). */
  today: string;
  /** The page's period: the chart opens on the span that holds it. */
  days: number;
}) {
  const [span, setSpan] = useState<number>(SPANS.find((s) => s >= days) ?? HISTORY);
  /** Days between the window's last day and today. */
  const [back, setBack] = useState(0);
  const [step, setStep] = useState<Step>("week");

  const byDay = new Map<string, { done: number; failed: number }>();
  for (const r of rows) {
    const day = byDay.get(r.day) ?? { done: 0, failed: 0 };
    byDay.set(r.day, { done: day.done + r.done, failed: day.failed + r.failed });
  }
  const end = Date.parse(`${today}T00:00:00Z`) - back * DAY;
  const dates = Array.from({ length: span }, (_, i) =>
    new Date(end - (span - 1 - i) * DAY).toISOString().slice(0, 10),
  );
  const totals = dates.map((d) => byDay.get(d) ?? { done: 0, failed: 0 });
  const top = niceTop(Math.max(...totals.map((t) => t.done + t.failed)));
  const share = (n: number) => `${(n / top) * 100}%`;
  const label = (date: string) => dayName.format(Date.parse(`${date}T00:00:00Z`));

  const at = SPANS.indexOf(span as (typeof SPANS)[number]);
  const furthest = HISTORY - span;
  const zoom = (to: number) => {
    setSpan(to);
    setBack(Math.min(back, HISTORY - to));
  };
  const move = (by: number) => setBack(Math.max(0, Math.min(furthest, back + by)));

  return (
    <Panel
      title="Board Reads per Day"
      className="@4xl:col-span-3"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <IconButton
            label="Zoom Out"
            onClick={() => zoom(SPANS[at + 1])}
            disabled={at === SPANS.length - 1}
          >
            <MagnifyingGlassMinusIcon size={16} aria-hidden />
          </IconButton>
          <span className="text-label text-ink-muted w-16 text-center font-normal tabular-nums">
            {span} days
          </span>
          <IconButton label="Zoom In" onClick={() => zoom(SPANS[at - 1])} disabled={at === 0}>
            <MagnifyingGlassPlusIcon size={16} aria-hidden />
          </IconButton>
          <span className="bg-border-subtle mx-1 h-5 w-px" aria-hidden />
          <IconButton
            label={`Back One ${step === "week" ? "Week" : "Month"}`}
            onClick={() => move(STEPS[step])}
            disabled={back >= furthest}
          >
            <CaretLeftIcon size={16} aria-hidden />
          </IconButton>
          <select
            aria-label="Move By"
            value={step}
            onChange={(e) => setStep(e.target.value as Step)}
            className="border-border-control bg-panel text-body text-ink focus-visible:ring-brand-ring rounded-control h-8 border px-2 focus-visible:ring-2 focus-visible:outline-none"
          >
            <option value="week">Week</option>
            <option value="month">Month</option>
          </select>
          <IconButton
            label={`Forward One ${step === "week" ? "Week" : "Month"}`}
            onClick={() => move(-STEPS[step])}
            disabled={back === 0}
          >
            <CaretRightIcon size={16} aria-hidden />
          </IconButton>
        </div>
      }
    >
      <figure className="flex h-full flex-col">
        <p className="text-label text-ink-muted mb-3 font-normal" aria-live="polite">
          {label(dates[0])} to {label(dates[span - 1])} (UTC)
        </p>
        <div className="flex min-h-52 flex-1 gap-3">
          <div className="text-label text-ink-meta flex w-10 flex-col justify-between text-right font-normal tabular-nums">
            <span className="-translate-y-1/2">{short.format(top)}</span>
            <span>{short.format(top / 2)}</span>
            <span className="translate-y-1/2">0</span>
          </div>
          <div className="relative min-w-0 flex-1">
            <div className="border-border-subtle absolute inset-x-0 top-0 border-t" />
            <div className="border-border-subtle absolute inset-x-0 top-1/2 border-t" />
            <div className="border-border-surface absolute inset-x-0 bottom-0 border-t" />
            <div className="absolute inset-0 flex items-end gap-0.5">
              {dates.map((date, i) => {
                const { done, failed } = totals[i];
                return (
                  <div
                    key={date}
                    title={`${label(date)}: ${count(done)} done, ${count(failed)} failed`}
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
        <div className="text-label text-ink-meta mt-2 flex justify-between pl-13 font-normal tabular-nums">
          <span>{label(dates[0])}</span>
          <span>{label(dates[Math.floor(span / 2)])}</span>
          <span>{label(dates[span - 1])}</span>
        </div>
        <figcaption className="text-label text-ink-muted mt-4 flex flex-wrap justify-center gap-5 font-normal">
          <Key swatch="bg-brand">Done</Key>
          <Key swatch="bg-danger">Failed</Key>
        </figcaption>
      </figure>
    </Panel>
  );
}
