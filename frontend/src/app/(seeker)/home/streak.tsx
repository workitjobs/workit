"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import { Skeleton } from "@/components/shadcn/skeleton";
import { StatTile, StatTileSkeleton } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { SegmentedToggle } from "@/components/ui/segmented-control";
import { cn } from "@/lib/cn";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";

import { localDay } from "../tracker";
import type { AppliedApplication } from "./data";
import { DayApplications } from "./day-applications";
import { SectionHeader } from "./section-header";
import { MORPH_MS, mountSkyline, type Skyline, type SkylineState } from "./streak-canvas";
import {
  buildGrid,
  computeStats,
  dayMs,
  monthLabels,
  type AppliedDay,
  type Cell,
} from "./streak-model";

/**
 * Activity — the seeker's year of applications as a streak heat map that folds
 * up into a 3D skyline and back, two columns wide at the foot of the
 * Home, beside Waiting.
 * It replaced a weekly pace chart there and kept its heading (page.tsx says
 * why).
 *
 * In a white card under its heading, like every Home section
 * (ui/card.tsx, `tone="tile"`). The view switch sits where a section's one way
 * onward does, at the top right, in the applications ViewSwitcher's segmented
 * style. Buttons rather than links, because the morph between the views is
 * the point and a navigation would cut it.
 *
 * Hover a day for its count, arrow keys walk the grid, and in 3D a drag
 * orbits (double-click resets). A click, a tap or Enter on a filled day opens
 * that day's applications in a table (./day-applications.tsx, KAN-423); a
 * tap on an empty day pins its count. There is no legend or hint row under the
 * stats: the tooltip gives any day's exact count, and darker reads as more
 * without a key. The canvas is ./streak-canvas.ts; the numbers come from
 * ./streak-model.ts. The numbers are ink, never a level's violet: colour
 * belongs to the marks.
 *
 * TODAY IS THE VIEWER'S. The current streak runs to today, or to yesterday
 * while today is still open, and which day that is depends on where the reader
 * is. The server renders UTC's today, the reader's own for most of the day,
 * and the browser swaps in its own after hydration — useSyncExternalStore
 * keeps that from being a mismatch, as PostedDate does in
 * company/jobs/jobs-table.tsx. Each application's day is the viewer's too, by
 * the same swap: it gets the instant it was sent (`applied`, from the live
 * tracker) and counts it on its UTC day until hydration, then on the
 * browser's own (KAN-342). A failed read draws no year at all: the page
 * shows `StreakFailed` instead, the card with Try Again (KAN-819), never
 * stand-in days or an empty year under a line that says so.
 *
 * Adapted from the Contribution Skyline component on 21st.dev.
 */

type View = "2d" | "3d";

const VIEW_OPTIONS = [
  { value: "2d" as const, label: "2D" },
  { value: "3d" as const, label: "3D" },
];

const NUMBER = new Intl.NumberFormat("en-US");
const DAY = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});
const DAY_YEAR = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});
const MONTH_YEAR = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const DAY_LONG = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const applications = (n: number) => (n === 1 ? "application" : "applications");
const daysWord = (n: number) => (n === 1 ? "day" : "days");
const counted = (n: number) => (n ? `${NUMBER.format(n)} ${applications(n)}` : "No applications");

/** "Aug 18 – Aug 26", or the one date when a run is a day long. */
const span = (a: string | null, b: string | null, withYear = false) => {
  if (!a || !b) return "—";
  const f = withYear ? DAY_YEAR : DAY;
  return a === b ? f.format(dayMs(a)) : `${f.format(dayMs(a))} – ${f.format(dayMs(b))}`;
};

const describe = (cell: Cell | undefined) =>
  cell ? `${counted(cell.count)} on ${DAY_LONG.format(dayMs(cell.date))}` : "";

const noSubscription = () => () => {};
const pad = (n: number) => String(n).padStart(2, "0");
const localToday = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const utcToday = () => new Date().toISOString().slice(0, 10);
const inBrowser = () => true;
const onServer = () => false;

export function Streak({
  applied,
  className,
}: {
  /** Each sent application (`StreakFailed` stands in when the tracker
   *  can't be read). */
  applied: AppliedApplication[];
  className?: string;
}) {
  const today = useSyncExternalStore(noSubscription, localToday, utcToday);
  const local = useSyncExternalStore(noSubscription, inBrowser, onServer);
  const days = useMemo<AppliedDay[]>(
    () =>
      applied.map((app) => ({
        date: local ? localDay(app.appliedOn) : app.appliedOn.slice(0, 10),
        count: 1,
      })),
    [applied, local],
  );
  const model = useMemo(() => {
    const grid = buildGrid(days, dayMs(today));
    return {
      ...grid,
      stats: computeStats(grid.cells),
      months: monthLabels(grid.cells, grid.weeks),
    };
  }, [days, today]);

  // The flat heat map first: it reads at a glance, and the skyline is the
  // flourish a seeker opts into.
  const [view, setView] = useState<View>("2d");
  const [active, setActive] = useState(-1);
  const [announcement, setAnnouncement] = useState("");
  // False until the canvas has drawn its first frame, which it can do only
  // once this component hydrates: until then the map's room holds a
  // skeleton bar. Without it the server's HTML drew the heading and the
  // numbers over 150px of blank white, which read as a section with no
  // loader, for as long as the page's script took to load and hydrate.
  const [drawn, setDrawn] = useState(false);
  // The day whose applications the dialog lists. Kept after it closes, so
  // the dialog keeps its words while it fades out.
  const [day, setDay] = useState<{ date: string; open: boolean } | null>(null);
  const dayApplications = useMemo(
    () =>
      day
        ? applied
            .filter((app) => localDay(app.appliedOn) === day.date)
            .sort((a, b) => Date.parse(a.appliedOn) - Date.parse(b.appliedOn))
        : [],
    [applied, day],
  );

  const rootRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const skyline = useRef<Skyline | null>(null);

  // What the drawing loop reads, refreshed after every render. Declared ahead
  // of the effects below, so it is current by the time they kick the loop.
  const snapshot: SkylineState = {
    model,
    target: view === "3d" ? 1 : 0,
    setActive,
    announce: (i) => setAnnouncement(describe(model.cells[i])),
    open: (i) => {
      const date = model.cells[i]?.date;
      if (date) setDay({ date, open: true });
    },
  };
  const live = useRef(snapshot);
  useEffect(() => {
    live.current = snapshot;
  });

  useEffect(() => {
    const root = rootRef.current;
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    const tip = tipRef.current;
    if (!root || !stage || !canvas || !tip) return;
    const engine = mountSkyline({ root, stage, canvas, tip }, live);
    skyline.current = engine;
    // mountSkyline paints its first frame before it returns.
    setDrawn(true);
    return () => {
      engine?.destroy();
      skyline.current = null;
    };
  }, []);

  useEffect(() => {
    skyline.current?.kick();
  }, [view]);

  useEffect(() => {
    skyline.current?.load();
  }, [model]);

  // The tooltip is kept inside the section by its width; measure it when its text changes.
  useLayoutEffect(() => {
    const tip = tipRef.current;
    if (tip && active >= 0) skyline.current?.tipWidth(tip.offsetWidth);
  }, [active, model]);

  const { stats } = model;
  const is3d = view === "3d";
  // The numbers belong to the heat map; the skyline stands alone.
  const showRow = !is3d;
  const cell = active >= 0 ? model.cells[active] : undefined;
  const blocks: StatBlock[] = [
    {
      label: "Past Year",
      value: stats.total,
      unit: applications(stats.total),
      sub: stats.first ? `Since ${MONTH_YEAR.format(dayMs(stats.first))}` : "None yet",
    },
    {
      label: "Busiest Day",
      value: stats.busiest.count,
      unit: applications(stats.busiest.count),
      sub: stats.busiest.date ? DAY.format(dayMs(stats.busiest.date)) : "None yet",
    },
    {
      label: "Longest Streak",
      value: stats.longest.days,
      unit: daysWord(stats.longest.days),
      sub: stats.longest.days ? span(stats.longest.start, stats.longest.end) : "None yet",
    },
    {
      label: "Current Streak",
      value: stats.current.days,
      unit: daysWord(stats.current.days),
      sub: stats.current.days ? span(stats.current.start, stats.current.end) : "Apply today",
    },
  ];

  return (
    <Card
      as="section"
      tone="tile"
      padding="lg"
      ref={rootRef}
      aria-labelledby="streak"
      className={cn("@container/streak", className)}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeader id="streak" title="Activity" />
        <SegmentedToggle
          label="Chart View"
          options={VIEW_OPTIONS}
          value={view}
          onValueChange={(v) => setView(v as View)}
        />
      </div>

      {/* One room for both views (./streak-canvas.ts, MAX_H2): a spacer the
          heat map's height, then the numbers, with the stage laid over the
          top. In 3D the stage grows over the numbers as they fade, so the
          section never changes height. */}
      <div className="relative mt-3">
        <div aria-hidden="true" style={{ height: "var(--streak-h2, 150px)" }} />

        {!drawn && (
          <Skeleton aria-hidden="true" className="absolute inset-x-0 top-0 z-10 h-[150px]" />
        )}

        <div
          aria-hidden={!showRow}
          inert={!showRow}
          className="ease-glide grid grid-cols-2 gap-3 pt-3 transition-opacity @2xl/streak:grid-cols-4"
          style={{
            opacity: showRow ? 1 : 0,
            // Out at once, ahead of the rising bars; back only once the
            // grid has folded flat above them.
            transitionDuration: showRow ? "300ms" : "200ms",
            transitionDelay: showRow ? `${MORPH_MS - 300}ms` : "0ms",
          }}
        >
          {blocks.map(({ label, value, unit, sub }) => (
            // The app's one stat tile (components/stat-tile.tsx, KAN-828),
            // as a grey well inside this card, its dates in a tag pill.
            <StatTile
              key={label}
              on="card"
              label={label}
              value={value}
              unit={unit}
              note={
                <Badge variant="tag" pill>
                  {sub}
                </Badge>
              }
            />
          ))}
        </div>

        <div
          ref={stageRef}
          className="outline-brand-ring absolute inset-x-0 top-0 overflow-hidden rounded-md outline-offset-4 has-[:focus-visible]:outline-2"
          style={{ height: 150 }}
        >
          <canvas
            ref={canvasRef}
            tabIndex={0}
            role="img"
            aria-label={`${counted(stats.total)} between ${span(stats.first, stats.last, true)}, shown as a ${is3d ? "3D skyline" : "heat map"}. Use the arrow keys to read individual days, and Enter to list a day's applications.`}
            className="absolute top-0 left-0 block max-w-none outline-none"
            style={{ touchAction: is3d ? "pan-y" : "auto" }}
          />
        </div>

        <div
          ref={tipRef}
          role="tooltip"
          aria-hidden={active < 0}
          className="bg-foreground text-background text-note pointer-events-none absolute top-0 left-0 z-20 rounded-md px-3 py-1.5 whitespace-nowrap shadow-lg transition-opacity duration-150"
          style={{ opacity: active >= 0 ? 1 : 0 }}
        >
          {cell ? (
            <>
              <strong className="font-semibold">{counted(cell.count)}</strong>
              <span className="opacity-75"> on {DAY_YEAR.format(dayMs(cell.date))}</span>
            </>
          ) : (
            " "
          )}
          <span
            aria-hidden="true"
            className="border-t-foreground absolute top-full -ml-[5px] size-0 border-x-[5px] border-t-[5px] border-x-transparent"
            style={{ left: "var(--arrow, 50%)" }}
          />
        </div>
      </div>

      {/* A live region only once hydrated (`local`), never in the server's
          HTML (KAN-829). React holds this streamed section in a hidden div at
          the end of <body> until it reveals it, outside the wrapper that
          ../settings/layout.tsx puts round Home; the Settings modal opening
          in that time kept this region and hid its siblings, the heading row
          and the map, and hydration found `aria-hidden` on two divs the
          browser draws without it. */}
      <p aria-live={local ? "polite" : undefined} className="sr-only">
        {announcement}
      </p>

      {day && (
        <DayApplications
          date={day.date}
          open={day.open}
          applications={dayApplications}
          onClose={() => setDay({ ...day, open: false })}
        />
      )}
    </Card>
  );
}

/**
 * Activity when the tracker can't be read (KAN-819): the card and its
 * heading over the failed read's compact card, with Try Again, which reads
 * the page again. A separate part, not a state of `Streak`, so a read that
 * works on Try Again mounts the canvas fresh: `Streak` mounts it once.
 */
export function StreakFailed({ className }: { className?: string }) {
  return (
    <Card as="section" tone="tile" padding="lg" aria-labelledby="streak" className={className}>
      <SectionHeader id="streak" title="Activity" />
      <LoadFailed compact title="Your Applications Aren't Loading Right Now" className="mt-3">
        We couldn&apos;t reach your tracker. Try again in a few minutes.
      </LoadFailed>
    </Card>
  );
}

type StatBlock = { label: string; value: number; unit: string; sub: string };

/*
 * Each number under the heat map is the app's one stat tile
 * (components/stat-tile.tsx, KAN-828) on `card`: a grey well, its label
 * over the figure, its unit beside it, and its dates in a pill under it,
 * each on a line of its own, so the four keep one shape whatever their
 * words. Home draws every date in a pill (docs/screens.md). The pill sat
 * on the label's line for a while, to save height, and wrapped under
 * "Current Streak" alone, which made that well taller than its three
 * siblings. A block with nothing to date says so in the pill ("None yet",
 * "Apply today"). Until KAN-828 the wells drew their label in meta grey
 * and the figure at --text-display, a third look beside Home's tiles and
 * an application's.
 */

/**
 * Activity while the tracker loads (Home streams it in its own
 * <Suspense>, and its loading.tsx draws it too): the heading as a bar, the
 * view switch's pill, the heat map's room at its default 150px (--streak-h2's
 * fallback, which the canvas resets to the map's own height on mount) and
 * the four wells, each the stat tile's own skeleton (StatTileSkeleton).
 * The section is the page's last, so a map a few
 * pixels taller than 150 moves nothing under it.
 */
export function StreakSkeleton({ className }: { className?: string }) {
  return (
    <Card
      as="section"
      tone="tile"
      padding="lg"
      aria-label="Activity"
      aria-busy="true"
      className={cn("@container/streak", className)}
    >
      <div aria-hidden="true" className="flex flex-wrap items-center justify-between gap-3">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-9 w-20 rounded-full" />
      </div>
      <div aria-hidden="true" className="mt-3">
        <Skeleton className="h-[150px] w-full" />
        <div className="grid grid-cols-2 gap-3 pt-3 @2xl/streak:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <StatTileSkeleton key={i} on="card" />
          ))}
        </div>
      </div>
    </Card>
  );
}
