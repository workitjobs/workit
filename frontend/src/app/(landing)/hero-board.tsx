import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

import { heroFits } from "./data";
import { FaviconLogo } from "./favicon-logo";

/** One turn of the lights, in s: each lit tile shows for about a third of
 *  it (`board-lit` in landing.css). */
const CYCLE = 14;

/**
 * The tiles, in the order the grid places them round the headline (row by
 * row, left and right of it in the middle rows). The most any width shows
 * is 26 (`.hero-grid` in landing.css: 4 columns on a phone, 6 from sm, 7
 * from lg, 9 from xl, with the headline 4 rows tall below 90rem and 3 from
 * it); each tile hides below the width that has a cell for it, or a spare
 * tile would open a new row.
 */
const TILES = 26;
function shownFrom(i: number) {
  if (i < 8) return undefined;
  if (i < 12) return "max-sm:hidden";
  if (i < 22) return "max-lg:hidden";
  if (i < 24) return "max-xl:hidden";
  return "max-xl:hidden min-[90rem]:hidden";
}

/**
 * The tiles that light up, each with its turn: tile index to its place in
 * the cycle, out of `heroFits.length`. Picked so the lit tiles spread over
 * the top, the sides and the bottom at every width, and so the few a phone
 * shows (tiles 1 and 6) light half a turn apart.
 */
const LIT: Record<number, number> = { 1: 0, 6: 4, 10: 2, 13: 5, 16: 1, 19: 6, 23: 3 };

/**
 * The home hero's grid (KAN-923, the user's pick): square white tiles round
 * the headline, which sits in one large white tile of its own, and the
 * tiles of the postings that fit you light up in soft violet, in turn,
 * with the company, the role and the match as a percentage over a bar
 * (`MatchBar`), as the Jobs page puts the best fits first. Soft violet is
 * the user's pick over the green of the first sketch. It
 * replaced a board of wide grey posting cards, which the user found
 * unsatisfying beside the sketch of this grid, and before it a violet mesh
 * gradient, too close to Calendly's. A server component with no script: the
 * lights are a CSS loop on opacity and transform (`.board-lit`), held by
 * Pause Animations, lit and still with reduced motion. The grid places the
 * headline tile in its middle and the small tiles flow round it
 * (`.hero-grid`); the tiles are decorative.
 */
export function HeroGrid({ children }: { children: ReactNode }) {
  return (
    <div className="hero-grid">
      <div className="hero-copy">{children}</div>
      {Array.from({ length: TILES }, (_, i) => {
        const turn = LIT[i];
        const posting = turn === undefined ? null : heroFits[turn];
        return (
          <div
            key={i}
            aria-hidden="true"
            className={cn("hero-tile relative rounded-2xl bg-white", shownFrom(i))}
          >
            {posting && (
              <div
                className="board-lit absolute inset-0 flex flex-col rounded-2xl p-2 sm:p-2.5 lg:p-3"
                style={
                  {
                    background: "color-mix(in oklab, var(--color-brand) 13%, white)",
                    "--d": `${-(turn * CYCLE) / heroFits.length}s`,
                    "--cycle": `${CYCLE}s`,
                  } as CSSProperties
                }
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  <FaviconLogo
                    domain={posting.domain}
                    eager
                    className="size-5 rounded-md shadow-none lg:size-6"
                  />
                  <span className="text-landing-brand-800 hidden truncate text-[11px] font-semibold lg:block">
                    {posting.company}
                  </span>
                </span>
                {/* The role, from lg up, where a tile has room for two lines
                    of it; below lg the tile shows the logo and the match. */}
                <span className="text-ink mt-1.5 line-clamp-2 hidden text-xs leading-tight font-semibold lg:block">
                  {posting.title}
                </span>
                <MatchBar score={posting.score} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * A match as a percentage over a slim bar filled to it: the number to read,
 * the bar to see at a glance, in about 20px of the tile's height. A ring
 * was tried first and took too much of a small tile (the user's call).
 * Still: the tile's light is the motion.
 */
function MatchBar({ score }: { score: number }) {
  return (
    <span className="mt-auto block">
      <span className="flex items-baseline gap-1">
        <span className="text-landing-brand-800 text-xs font-bold tabular-nums lg:text-sm">
          {score}%
        </span>
        <span className="text-landing-brand-800/80 hidden text-[11px] font-medium lg:inline">
          match
        </span>
      </span>
      <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-white/80">
        <span className="bg-brand block h-full rounded-full" style={{ width: `${score}%` }} />
      </span>
    </span>
  );
}
