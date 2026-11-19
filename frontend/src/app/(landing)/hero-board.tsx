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
 * Each tile's posting (an index into `heroFits`): every posting on four
 * tiles spread over the top, the sides and the bottom, so a fit turns up
 * anywhere. The eight a phone shows (tiles 0 to 7) hold all seven postings.
 */
const POSTING_OF = [
  3, 0, 5, 1, 6, 2, 4, 3, 6, 0, 2, 4, 1, 5, 0, 3, 1, 2, 4, 6, 5, 6, 2, 3, 0, 4, 1, 5,
];

/**
 * The order the tiles light, one at a time, for each layout, by how many
 * tiles it shows (`.hero-grid` in landing.css: 8 on a phone, 12 from sm,
 * 20, 24 or 28 from lg by the screen's shape): every shown tile once a
 * loop. Shuffled so the cards turn up all over the grid, never two
 * neighbours (tiles within two of each other) in a row and never the same
 * posting twice in a row, the loop's end into its start included. Picked
 * by a script; keep both rules if you change one. The user found several
 * cards lit at once overlapping, and one 14s loop over seven fixed tiles,
 * before that, too orderly.
 */
const ORDERS: Record<number, number[]> = {
  8: [4, 0, 5, 2, 7, 3, 6, 1],
  12: [3, 10, 6, 0, 9, 4, 11, 2, 5, 8, 1, 7],
  20: [1, 5, 2, 18, 8, 17, 6, 19, 0, 16, 11, 4, 7, 14, 3, 15, 10, 13, 9, 12],
  24: [12, 17, 1, 6, 10, 21, 14, 7, 3, 20, 9, 16, 4, 23, 19, 11, 8, 0, 13, 22, 15, 5, 2, 18],
  28: [
    23, 6, 21, 27, 12, 20, 10, 4, 22, 2, 24, 11, 17, 26, 1, 15, 5, 19, 13, 18, 3, 9, 25, 0, 8, 16,
    7, 14,
  ],
};

/** A tile's turn in each layout that shows it, as `--s<n>` for landing.css
 *  (`.board-lit`), which picks the one for the screen. */
function turnsOf(tile: number) {
  const turns: Record<string, number> = {};
  for (const [count, order] of Object.entries(ORDERS)) {
    const turn = order.indexOf(tile);
    if (turn >= 0) turns[`--s${count}`] = turn;
  }
  return turns as CSSProperties;
}

/** The tiles lit, and still, with reduced motion: one per posting, spread
 *  over the grid at every width. */
const STILL = new Set([1, 6, 10, 13, 16, 19, 23]);

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
 * lights are one CSS loop on opacity and transform (`.board-lit`), a card at
 * a time in a shuffled order (`ORDERS`); with reduced motion one
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
        const posting = heroFits[POSTING_OF[i]];
        return (
          <div key={i} aria-hidden="true" className="hero-tile relative rounded-2xl">
            <div
              data-still={STILL.has(i) || undefined}
              className="board-lit absolute inset-0 flex flex-col rounded-2xl p-2 sm:p-2.5 lg:p-3"
              style={turnsOf(i)}
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
