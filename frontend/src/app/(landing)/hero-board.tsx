import type { CSSProperties, ReactNode } from "react";

import { MatchGlyph } from "@/components/match-badge";
import { matchColor, matchTier } from "@/lib/match";

import { heroFits } from "./data";
import { FaviconLogo } from "./favicon-logo";

/**
 * The tiles, in the order the grid places them round the headline (row by
 * row, left and right of it in the middle rows). The most any screen shows
 * is 28 (11 columns on an ultrawide screen); `.hero-grid` in landing.css
 * shows only as many as the screen's grid has cells for, or a spare tile
 * would open a new row.
 */
const TILES = 28;

/**
 * Where each posting can light (KAN-923): every tile is a place, and each
 * posting (an index into `heroFits`) has four, spread over the top, the
 * sides and the bottom, so a fit turns up anywhere, not on the same seven
 * tiles in the same order, which the user found too orderly. The eight a
 * phone shows (tiles 0 to 7) hold all seven postings.
 */
const POSTING_OF = [
  3, 0, 5, 1, 6, 2, 4, 3, 6, 0, 2, 4, 1, 5, 0, 3, 1, 2, 4, 6, 5, 6, 2, 3, 0, 4, 1, 5,
];

/**
 * Each posting's own loop, in s. The lengths share no rhythm, so the lights
 * across the grid never settle into a pattern a visitor could learn: the
 * whole grid only repeats after hours. Each tile lights for about an eighth
 * of its posting's loop (`board-lit` in landing.css), 2.6 to 4 s.
 */
const LOOPS = [23, 29, 26, 31, 22, 34, 27];

/** Where each posting's loop starts, as a share of it, so the grid opens
 *  mid-flow with a few tiles already lit. */
const PHASES = [0.13, 0.71, 0.42, 0.88, 0.27, 0.56, 0.95];

/**
 * The order a posting's four tiles take their turns, a quarter loop apart:
 * one at a time, since a tile is lit for less than a quarter of the loop,
 * so the same posting never shows twice at once. Not in tile order, which
 * would walk it along the grid.
 */
const TURN_ORDER = [0, 2, 1, 3];

/** The tiles lit, and still, with reduced motion: one per posting, spread
 *  over the grid at every width. */
const STILL = new Set([1, 6, 10, 13, 16, 19, 23]);

/** A tile's posting and its place in that posting's loop, as CSS's delay. */
function lightOf(tile: number) {
  const posting = POSTING_OF[tile];
  const turn = POSTING_OF.slice(0, tile).filter((p) => p === posting).length;
  const loop = LOOPS[posting];
  return {
    posting: heroFits[posting],
    loop,
    delay: -(PHASES[posting] + TURN_ORDER[turn] / 4) * loop,
  };
}

/**
 * The home hero's grid (KAN-923, the user's pick): square glass tiles over a
 * grainy violet ground (`.hero-ground`, `.hero-tile` in landing.css) round
 * the headline, which sits in one large solid white tile of its own, and
 * the tiles of postings worth applying to light up in turn as bright glass
 * cards (`.board-lit`), with the company, the role and the match's strength
 * in the app's bands over a filling bar (`MatchBar`), as the Jobs page puts
 * the best fits first. Their text is ink in the Jobs page job card's
 * weights (compact-job-card.tsx: the role medium, the company regular, the
 * band semibold), and the match is in the app's own colours. Solid violet
 * lit tiles with white text came before the glass, which the user asked
 * for; before them a board of wide grey posting cards, which the user found
 * unsatisfying beside the sketch of this grid, and a violet mesh gradient,
 * too close to Calendly's. A server component with no script: the
 * lights are CSS loops on opacity and transform (`.board-lit`), one length
 * per posting (`LOOPS`); with reduced motion one
 * tile per posting is lit and still (`STILL`). The grid fills the
 * hero panel edge to edge, the headline's tile in its middle and the small
 * tiles flowing round it, with as many columns as keep the tiles near
 * square (`.hero-grid`); the tiles are decorative.
 */
export function HeroGrid({ children }: { children: ReactNode }) {
  return (
    <div className="hero-grid">
      <div className="hero-copy">{children}</div>
      {Array.from({ length: TILES }, (_, i) => {
        const { posting, loop, delay } = lightOf(i);
        return (
          <div key={i} aria-hidden="true" className="hero-tile relative rounded-2xl">
            <div
              data-still={STILL.has(i) || undefined}
              className="board-lit absolute inset-0 flex flex-col rounded-2xl p-2 sm:p-2.5 lg:p-3"
              style={{ "--d": `${delay.toFixed(2)}s`, "--cycle": `${loop}s` } as CSSProperties}
            >
              <span className="flex min-w-0 items-center gap-1.5">
                <FaviconLogo
                  domain={posting.domain}
                  eager
                  className="size-5 rounded-md lg:size-6"
                />
                <span className="text-ink-muted hidden truncate text-xs font-normal lg:block">
                  {posting.company}
                </span>
              </span>
              {/* The role, from lg up, in two lines, one or none by the
                    tile's height (`.tile-role` in landing.css), so it never
                    runs into the match. */}
              <span className="tile-role text-ink mt-1.5 text-[13px] leading-tight font-medium">
                {posting.title}
              </span>
              <MatchBar score={posting.score} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * A match's strength, as the Jobs page names it: the app's band
 * (`matchTier`: Excellent, Good, Fair or Weak Match) behind the app's own
 * match ring (`MatchGlyph`, the match badge's 14px ring; the user picked it over signal bars,
 * band icons and a target, and over the dot it replaced), then a slim
 * bar filled to the score with the percentage at its end. The band leads
 * because a number alone does not tell a student whether to apply (the
 * user's call); the bar and the number back it up. On a narrow tile the
 * band drops its "Match" and the number goes (`.tile-*` container rules in
 * landing.css). The bar fills each time the tile lights (`.board-bar`).
 * A ring was tried first and took too much of a small tile.
 */
function MatchBar({ score }: { score: number }) {
  const tier = matchTier(score);
  return (
    // Two groups, by proximity: the job (company, role) and the verdict
    // (band, bar, percentage). The verdict sits at the tile's foot at least
    // 10px under the role (`pt-2.5`), with only 4px from the band to its bar
    // (`mt-1`), so it reads with its bar; at 6px each way it read as part
    // of the role (the user's catch).
    <span className="mt-auto block pt-2.5">
      <span className="flex items-center gap-1.5">
        <MatchGlyph score={score} className="tile-mark lg:size-4" />
        <span className="text-ink truncate text-[11px] font-semibold lg:text-xs">
          <span className="tile-tier-full">{tier}</span>
          <span className="tile-tier-short">{tier.replace(/ Match$/, "")}</span>
        </span>
      </span>
      <span className="mt-1 flex items-center gap-1.5">
        <span className="bg-ink/10 block h-1.5 flex-1 overflow-hidden rounded-full">
          <span
            className="board-bar block h-full rounded-full"
            style={{ width: `${score}%`, background: matchColor(score) }}
          />
        </span>
        <span className="tile-pct text-ink-muted text-[11px] font-normal tabular-nums">
          {score}%
        </span>
      </span>
    </span>
  );
}
