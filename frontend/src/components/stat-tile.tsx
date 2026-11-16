import Link from "next/link";
import type { ComponentType, ReactNode } from "react";

import { ArrowRightIcon, TrendIcon } from "@/components/icons";
import { Skeleton } from "@/components/shadcn/skeleton";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatCount } from "@/lib/format-count";

export type StatDelta = {
  value: number;
  /** "last week" — printed after "vs". */
  period: string;
  /** Whether a rise is the good direction. More applicants: yes. More sitting
   *  unreviewed: no. Decides how the delta is coloured. */
  upIsGood: boolean;
};

/**
 * Where a tile stands, which sets only its fill, corner and padding:
 * `page`, a raised Home tile on the page ground (`Card tone="tile"`);
 * `card`, a grey well inside a white card (Activity's numbers); `tint`, a
 * white box with a hairline inside a tinted card (an application's Open
 * and Days Since, beside the match box, which is drawn the same way).
 */
export type StatTileOn = "page" | "card" | "tint";

/**
 * ONE STAT TILE (KAN-828): a label, a figure, and a line under it. Home's
 * four numbers, Activity's four and an application's two were three
 * looks until then: white tiles with a glyph chip, grey wells with the
 * label in meta grey and a smaller figure, and white cards with the figure
 * above its words in a third size. Now each is this tile, and only `on`
 * changes, by what it stands on: the label in 14px medium ink, the figure
 * in --text-figure with its unit beside it, then the line (a note, a date
 * pill, or a change against a period), always drawn, so a row of tiles
 * keeps one height. The company Overview keeps its `plain` row, below.
 *
 * `href` makes the whole tile a link (KAN-342): the label is the link,
 * stretched over the tile, which lifts 2px onto --shadow-lift under the
 * pointer and settles on the press; with `Icon`, the glyph in its tinted
 * chip slides out as an arrow slides in, so the tile says where it goes.
 * A keyboard focus rings the tile. The chip shows only where the tile has
 * room beside its label (10.5rem); the row keeps the chip's 36px either
 * way, so every figure in a row sits on one line.
 *
 * The value uses the font's proportional figures rather than tabular ones.
 * tabular-nums gives every digit the width of a zero, which keeps a column
 * of numbers aligned in a table; at 36px in a tile it makes 214 look gappy.
 * A number counts to its new value when it changes (ui/animated-number.tsx),
 * and the line under it fades in again, keyed on what it says.
 *
 * THE CHANGE IS A SMALL BOXED FIGURE before its words ("+3 ↑ vs last
 * week"), coloured by direction x whether up is good, not by direction
 * alone: more applicants arriving is good; more sitting unreviewed is not.
 * Zero is its own case: no box and no arrow, "Same as last week", since a
 * signless 0 in red read as a fall. The arrow carries direction on its
 * own, so neither reading depends on colour. "vs last week" hides below
 * 8.5rem of tile, where it wrapped under the box and lifted the figure.
 */
export function StatTile({
  label,
  Icon,
  tone = "bg-kpi-saved-chip text-kpi-saved",
  value,
  suffix = "",
  unit,
  delta,
  note,
  href,
  on = "page",
  plain = false,
}: {
  label: string;
  /** The glyph in the tile's chip at its top right. Decoration only: the
   *  label already says what the number is. */
  Icon?: ComponentType<{ className?: string }>;
  /** The chip's tint and glyph colour, a --color-kpi-* pair. */
  tone?: string;
  /** A number counts (AnimatedNumber); words print as they are ("Open");
   *  null is a dash, for a figure that couldn't load. */
  value: number | string | null;
  /** Printed right after the value — "%" for a rate. */
  suffix?: string;
  /** The value's unit in body text beside it: "applications", "days". */
  unit?: string;
  delta?: StatDelta;
  /** The line under the figure when there is no delta: words ("Since
   *  Aug 4") or a date pill. A non-breaking space at worst. */
  note?: ReactNode;
  /** Makes the whole tile a link to the list it counts. */
  href?: string;
  on?: StatTileOn;
  /** The company Overview's row: open on the page, the label on a hairline
   *  and the direction a small round marker beside it. Ignores `on`,
   *  `Icon`, `unit` and `href`. */
  plain?: boolean;
}) {
  if (plain) {
    const moved = delta && delta.value !== 0;
    const good = delta ? isGood(delta.value, delta.upIsGood) : false;

    return (
      <div>
        <div className="border-border-subtle flex items-center justify-between gap-2 border-b pb-2">
          <p className="text-note text-ink-meta">{label}</p>
          {/* The marker carries direction by its arrow, not only its
              colour, and the line below says the size of the change. */}
          {moved && (
            <span
              key={good ? "good" : "bad"}
              aria-hidden="true"
              className={cn(
                "animate-pop flex size-4 shrink-0 items-center justify-center rounded-full text-white",
                // positive-ink, not positive: white on #17b076 is 2.80:1, and
                // the delta text under it is already this green (5.35:1).
                good ? "bg-positive-ink" : "bg-danger",
              )}
            >
              <TrendIcon className="size-3" down={delta.value < 0} />
            </span>
          )}
        </div>

        <p className="text-display text-ink mt-2">
          {typeof value === "number" ? <AnimatedNumber value={value} /> : (value ?? "–")}
          {suffix}
        </p>

        {/* Always present, with a non-breaking space at worst: the Season
            window has no delta, and dropping the line shortened the whole
            row, so everything under it jumped when the range changed. */}
        {!delta && (
          <p
            key={typeof note === "string" ? note : undefined}
            className="text-note text-ink-meta animate-fade mt-0.5"
          >
            {note ?? " "}
          </p>
        )}
        {delta && (
          <p
            key={`${delta.value} ${delta.period}`}
            className="text-note text-ink-meta animate-fade mt-0.5"
          >
            {/* "Same as" rather than "No change vs": a narrow column wrapped
                the longer phrase onto a second line, the one tile in the row
                that did. */}
            {delta.value === 0 ? (
              `Same as ${delta.period}`
            ) : (
              <span className={cn("font-semibold", good ? "text-positive-ink" : "text-danger")}>
                {delta.value > 0 ? "+" : "−"}
                {formatCount(Math.abs(delta.value))}
                {suffix}
              </span>
            )}
            {delta.value !== 0 && ` vs ${delta.period}`}
          </p>
        )}
      </div>
    );
  }

  return (
    <Frame on={on} link={href !== undefined}>
      <div className={cn("flex items-center justify-between gap-3", Icon ? "min-h-9" : "min-h-5")}>
        {href ? (
          <Link
            href={href}
            className={cn(
              LABEL,
              // The overlay sits over the figure too, which is layered (its
              // count animates), so a click anywhere on the tile lands.
              "after:absolute after:inset-0 after:z-10 focus-visible:outline-none",
            )}
          >
            {label}
          </Link>
        ) : (
          <p className={LABEL}>{label}</p>
        )}
        {Icon && (
          <span
            aria-hidden="true"
            className={cn(
              // Only where the tile has room beside its label: in the
              // narrowest four-column layout a long label wrapped and
              // dropped its figure below the other three.
              "rounded-control relative hidden size-9 shrink-0 items-center justify-center overflow-hidden @[10.5rem]/stat:flex",
              tone,
            )}
          >
            <Icon
              aria-hidden
              className={cn(
                "size-4",
                href &&
                  "ease-glide transition-[translate,opacity] duration-200 group-hover/stat:translate-x-5 group-hover/stat:opacity-0 motion-reduce:transition-none",
              )}
            />
            {href && (
              <ArrowRightIcon className="ease-glide absolute size-4 -translate-x-5 opacity-0 transition-[translate,opacity] duration-200 group-hover/stat:translate-x-0 group-hover/stat:opacity-100 motion-reduce:transition-none" />
            )}
          </span>
        )}
      </div>

      {/* Pushed to the foot: a label that wraps makes its tile taller, the
          row stretches the others to match, and every figure in the row
          still sits on one line. */}
      <p className="text-figure text-ink mt-auto flex flex-wrap items-baseline gap-x-1.5 pt-3">
        <span>
          {typeof value === "number" ? <AnimatedNumber value={value} /> : (value ?? "–")}
          {value !== null && suffix}
        </span>
        {unit && value !== null && <span className="text-body text-ink-muted">{unit}</span>}
      </p>

      {/* Always one line at least, a non-breaking space at worst, so a row
          of tiles keeps one height whatever each has to say. */}
      <div
        key={delta ? `${delta.value} ${delta.period}` : typeof note === "string" ? note : undefined}
        className="text-note text-ink-meta animate-fade mt-2 flex min-h-5 items-center gap-1.5"
      >
        {delta ? <Change delta={delta} suffix={suffix} /> : (note ?? " ")}
      </div>
    </Frame>
  );
}

const LABEL = "text-body text-ink font-medium";

/** The tile's box, by what it stands on. A linked tile lifts under the
 *  pointer and rings on a keyboard focus. */
function Frame({
  on,
  link = false,
  className,
  children,
  ...props
}: {
  on: StatTileOn;
  link?: boolean;
  className?: string;
  children: ReactNode;
  "aria-hidden"?: boolean;
}) {
  const classes = cn(
    "@container/stat flex min-w-0 flex-col",
    link && [
      "group/stat",
      // Lifts 2px onto --shadow-lift under the pointer and settles on the
      // press, as a whole-target card does (docs/motion.md).
      "ease-glide hover:shadow-lift transition-[translate,scale,box-shadow] duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.99] active:duration-150",
      "motion-reduce:transition-none motion-reduce:hover:translate-y-0",
      "has-[a:focus-visible]:ring-brand-ring has-[a:focus-visible]:ring-2",
    ],
    className,
  );

  if (on === "page") {
    return (
      <Card tone="tile" padding="lg" as="div" className={classes} {...props}>
        {children}
      </Card>
    );
  }
  return (
    <div
      className={cn(
        "rounded-card relative p-4",
        on === "card" ? "bg-well" : "bg-panel border-border-subtle border",
        classes,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/** A change against a period: the boxed figure, then its words. */
function Change({ delta, suffix }: { delta: StatDelta; suffix: string }) {
  if (delta.value === 0) return <>Same as {delta.period}</>;
  const good = isGood(delta.value, delta.upIsGood);
  return (
    <>
      <span
        className={cn(
          "inline-flex items-center gap-0.5 rounded-md border px-1 font-semibold tabular-nums",
          good ? "border-positive/40 text-positive-ink" : "border-danger/40 text-danger",
        )}
      >
        {delta.value > 0 ? "+" : "−"}
        {formatCount(Math.abs(delta.value))}
        {suffix}
        <TrendIcon className="size-3" down={delta.value < 0} />
      </span>
      {/* Beside the box only where the tile has room for both: on a phone
          "vs last week" wrapped under it and lifted the figure above its
          row. */}
      <span className="hidden whitespace-nowrap @[8.5rem]/stat:inline">vs {delta.period}</span>
    </>
  );
}

/**
 * A tile while its number loads: the same box, with a bar in place of the
 * label, the figure and the line, each at its line's height, so nothing
 * under the row moves when the numbers land. `chip` keeps the label row at
 * the chip's 36px, as the real tile's is.
 */
export function StatTileSkeleton({
  on = "page",
  chip = false,
}: {
  on?: StatTileOn;
  chip?: boolean;
}) {
  return (
    <Frame on={on} aria-hidden>
      <div className={cn("flex items-center", chip ? "min-h-9" : "min-h-5")}>
        <Skeleton className="h-4 w-24 max-w-full" />
      </div>
      <div className="mt-auto pt-3">
        <Skeleton className="h-10 w-16" />
      </div>
      <div className="mt-2 flex min-h-5 items-center">
        <Skeleton className="h-3 w-28 max-w-full" />
      </div>
    </Frame>
  );
}

function isGood(value: number, upIsGood: boolean) {
  return value > 0 === upIsGood;
}
