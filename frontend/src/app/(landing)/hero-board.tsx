import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { HERO_FIT, heroBoard } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { scoreTone } from "./score-tone";

/** The board's rows and the postings per row (wider than any screen, so a
 *  row's ends are always cut by the panel). */
const ROWS = 6;
const PER_ROW = 7;
/** One turn of the lights, in s: each fitting posting is lit for about a
 *  third of it (`board-lit` in landing.css). */
const CYCLE = 18;

/**
 * The home hero's ground (KAN-923, the user's pick from four directions):
 * a board of real job postings around the headline, grey, and the ones that
 * fit you (`HERO_FIT` and up) light up in turn with their match, as the
 * Jobs page puts the best fits first. It replaced a violet-to-blue mesh
 * gradient, which the user found too close to Calendly's and without
 * feel. A server component: the lights are a CSS loop on opacity
 * (`.board-lit`), held by Pause Animations and lit still with reduced
 * motion. From lg up the headline sits in a clear hole in the board
 * (`.hero-board`'s mask); below lg the board is a band above it. Each
 * posting is drawn once grey, and a fitting one again, lit, over it, so the
 * light is one opacity change. Decorative: the headline says the same.
 */
export function HeroBoard() {
  const rows = Array.from({ length: ROWS }, (_, row) =>
    Array.from({ length: PER_ROW }, (_, col) => heroBoard[(row * 5 + col * 3) % heroBoard.length]),
  );
  // The fitting postings take turns across the whole board, evenly spaced
  // round the cycle, counted in reading order.
  const fitCount = rows.flat().filter((posting) => posting.score >= HERO_FIT).length;
  let lit = 0;
  return (
    <div
      aria-hidden="true"
      className="hero-board pointer-events-none absolute inset-x-0 top-0 select-none"
    >
      <div className="flex flex-col gap-3 pt-4 sm:pt-6">
        {rows.map((postings, row) => (
          <div
            key={row}
            // Every other row sits half a posting over, like laid bricks.
            className={cn(
              "flex justify-center gap-3",
              row % 2 === 1 && "translate-x-[5.9rem] sm:translate-x-[7.1rem]",
            )}
          >
            {postings.map((posting, col) => {
              const fits = posting.score >= HERO_FIT;
              const delay = fits ? -((lit++ * CYCLE) / fitCount) : 0;
              return (
                <div
                  key={col}
                  className="relative flex h-14 w-[11rem] shrink-0 items-center gap-2.5 rounded-2xl bg-white/70 px-3 shadow-[0_0_0_1px_rgb(15_23_42/0.04)] sm:h-16 sm:w-[13.5rem]"
                >
                  <FaviconLogo
                    domain={posting.domain}
                    eager
                    className="size-7 rounded-lg opacity-50 grayscale"
                  />
                  <Lines posting={posting} muted />
                  {fits && (
                    <div
                      className="board-lit absolute inset-0 flex items-center gap-2.5 rounded-2xl bg-white px-3 shadow-[var(--mk-shadow-float)]"
                      style={{ "--d": `${delay}s`, "--cycle": `${CYCLE}s` } as CSSProperties}
                    >
                      <FaviconLogo domain={posting.domain} eager className="size-7 rounded-lg" />
                      <Lines posting={posting} />
                      <span
                        className={cn(
                          "shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-bold tabular-nums ring-1 ring-inset",
                          scoreTone(posting.score),
                        )}
                      >
                        {posting.score}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function Lines({ posting, muted }: { posting: (typeof heroBoard)[number]; muted?: boolean }) {
  return (
    <span className="min-w-0 flex-1 text-left">
      <span
        className={cn(
          "block truncate text-xs font-semibold sm:text-[13px]",
          muted ? "text-slate-400" : "text-ink",
        )}
      >
        {posting.title}
      </span>
      <span
        className={cn("block truncate text-[11px]", muted ? "text-slate-400/80" : "text-ink-meta")}
      >
        {posting.company}
      </span>
    </span>
  );
}
