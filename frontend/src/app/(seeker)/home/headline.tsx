"use client";

import type { ComponentType } from "react";

import { AppliedIcon, BookmarkIcon, InterviewIcon, MatchIcon } from "@/components/icons";
import { StatTile, StatTileSkeleton } from "@/components/stat-tile";

import type { HomeStat, StatKey } from "./data";
import { RANGES, type RangeKey } from "./range";
import { useRange } from "./range-switch";

/** Each tile's glyph, by what it counts: the data is plain, so the icons stay
 *  on this side of the server boundary. */
const STAT_ICONS: Record<StatKey, ComponentType<{ className?: string }>> = {
  strongMatches: MatchIcon,
  saved: BookmarkIcon,
  applied: AppliedIcon,
  interviewing: InterviewIcon,
};

/**
 * Each tile's colours (KAN-423), as the user picked them: Excellent Matches
 * green, Saved grey, Applied violet, Interviewing yellow. Since 2026-11-09
 * the tile is white and the colour is only a small tinted chip at its top
 * right, with the glyph in that chip's own colour (the --color-kpi-* set in
 * globals.css, one lightness and strength for all four). The tiles were
 * tinted with the stage tints of ../stage-colors.ts and wore a white glyph
 * in a solid disc; the user found the four shades wrong (Saved the darkest
 * and dullest, green and amber each with a disc of another hue), and chose
 * white tiles with chips over a matched set of tinted tiles. Each glyph is
 * 3.97:1 or better on its chip. Magenta (the match ramp), a burnt amber and
 * solid fills were tried first and turned down.
 */
/** The tiles' order, for the skeleton: getHeadline's order in ./data.ts. */
const STAT_ORDER: StatKey[] = ["strongMatches", "saved", "applied", "interviewing"];

const STAT_TONE: Record<StatKey, string> = {
  strongMatches: "bg-kpi-match-chip text-kpi-match",
  saved: "bg-kpi-saved-chip text-kpi-saved",
  applied: "bg-kpi-applied-chip text-kpi-applied",
  interviewing: "bg-kpi-interviewing-chip text-kpi-interviewing",
};

/**
 * The headline numbers for the range in the URL, one tile each, four across
 * the top of Home. It is handed every range's figures and picks one
 * in the browser, so moving the range switch counts each figure to its new
 * value at once (AnimatedNumber) rather than after the server has drawn the
 * page again.
 *
 * Each is the app's one stat tile (components/stat-tile.tsx, KAN-828), on
 * the page ground, wearing its glyph in a small chip tinted with its own
 * colour (STAT_TONE), so the four stand apart at a glance without four
 * loud blocks. Excellent Matches was the one filled tile, in violet, until
 * then: violet is Applied's stage colour, so the filled tile and the
 * Applied badges said two things in one colour.
 *
 * EVERY TILE IS A LINK (KAN-342): a click anywhere on a tile opens the page
 * that lists what it counts (the Applications list filtered to its stage,
 * or the Jobs page in Best Match order). The tile lifts under the pointer
 * and its glyph slides out of its chip as an arrow slides in; the tile
 * draws all of that from its `href`.
 */
export function Headline({ stats }: { stats: Record<RangeKey, HomeStat[]> }) {
  const range = useRange();
  const { period, note } = RANGES.find((option) => option.key === range)!;

  // A fragment, not a wrapper: each number is its own tile on the page's grid.
  return (
    <>
      {stats[range].map((stat) => {
        const change =
          stat.value !== null && stat.previous !== null && period
            ? stat.value - stat.previous
            : null;

        return (
          <StatTile
            key={stat.key}
            href={stat.href}
            label={stat.label}
            Icon={STAT_ICONS[stat.key]}
            tone={STAT_TONE[stat.key]}
            value={stat.value}
            suffix={stat.suffix}
            delta={
              change === null || !period ? undefined : { value: change, period, upIsGood: true }
            }
            note={stat.note ?? (stat.value === null ? "Couldn't load" : note)}
          />
        );
      })}
    </>
  );
}

/**
 * The four numbers while they load (page.tsx streams them in their own
 * <Suspense>, and ./loading.tsx draws the page with these): each the
 * tile's own skeleton, with the chip's 36px row, so the grid holds its
 * height and nothing under it moves when the figures land. A fragment, as
 * Headline is: each tile is a cell of the page's grid.
 *
 * A streamed tile mounts with its figure, and AnimatedNumber prints a first
 * value as it is, so nothing counts up from 0 when the numbers arrive.
 */
export function HeadlineSkeleton() {
  return (
    <>
      {STAT_ORDER.map((key) => (
        <StatTileSkeleton key={key} chip />
      ))}
    </>
  );
}
