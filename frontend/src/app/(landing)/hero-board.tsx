import type { CSSProperties, ReactNode } from "react";

import { heroFits } from "./data";
import { FaviconLogo } from "./favicon-logo";

/** One turn of the lights, in s: each lit tile shows for about a third of
 *  it (`board-lit` in landing.css). */
const CYCLE = 14;

/**
 * The tiles, in the order the grid places them round the headline (row by
 * row, left and right of it in the middle rows). The most any screen shows
 * is 28 (11 columns on an ultrawide screen); `.hero-grid` in landing.css
 * shows only as many as the screen's grid has cells for, or a spare tile
 * would open a new row.
 */
const TILES = 28;

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
 * tiles of the postings that fit you light up in solid brand violet, in
 * turn, with the company, the role and the match as a percentage over a
 * bar (`MatchBar`), as the Jobs page puts the best fits first. Their text
 * is white in the Jobs page job card's weights (compact-job-card.tsx: the
 * role medium, the company regular, the match semibold), never violet on
 * violet, which the user found off; 85% white keeps 5:1 on the brand. It
 * replaced a board of wide grey posting cards, which the user found
 * unsatisfying beside the sketch of this grid, and before it a violet mesh
 * gradient, too close to Calendly's. A server component with no script: the
 * lights are a CSS loop on opacity and transform (`.board-lit`), held by
 * Pause Animations, lit and still with reduced motion. The grid fills the
 * hero panel edge to edge, the headline's tile in its middle and the small
 * tiles flowing round it, with as many columns as keep the tiles near
 * square (`.hero-grid`); the tiles are decorative.
 */
export function HeroGrid({ children }: { children: ReactNode }) {
  return (
    <div className="hero-grid">
      <div className="hero-copy">{children}</div>
      {Array.from({ length: TILES }, (_, i) => {
        const turn = LIT[i];
        const posting = turn === undefined ? null : heroFits[turn];
        return (
          <div key={i} aria-hidden="true" className="hero-tile relative rounded-2xl">
            {posting && (
              <div
                className="board-lit absolute inset-0 flex flex-col rounded-2xl p-2 sm:p-2.5 lg:p-3"
                style={
                  {
                    background: "var(--color-brand)",
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
                  <span className="hidden truncate text-xs font-normal text-white/85 lg:block">
                    {posting.company}
                  </span>
                </span>
                {/* The role, from lg up and on a tile at least 116px tall
                    (`.tile-role` in landing.css), where it has room for two
                    lines; otherwise the tile shows the company and match. */}
                <span className="tile-role mt-1.5 line-clamp-2 hidden text-[13px] leading-tight font-medium text-white lg:block">
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
 * The bar fills from empty each time its tile lights (`.board-bar` in
 * landing.css, on the tile's own cycle).
 */
function MatchBar({ score }: { score: number }) {
  return (
    <span className="mt-auto block">
      <span className="flex items-baseline gap-1">
        <span className="text-xs font-semibold text-white tabular-nums lg:text-sm">{score}%</span>
        <span className="hidden text-[11px] font-normal text-white/85 lg:inline">match</span>
      </span>
      <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-white/25">
        <span
          className="board-bar block h-full rounded-full bg-white"
          style={{ width: `${score}%` }}
        />
      </span>
    </span>
  );
}
