"use client";

import {
  BrowsersIcon,
  CalendarDotsIcon,
  ClipboardTextIcon,
  FileTextIcon,
  FunctionIcon,
  GlobeSimpleIcon,
  NotePencilIcon,
  TableIcon,
} from "@phosphor-icons/react/ssr";
import { useScroll } from "motion/react";
import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

import { toolsCollapse } from "./data";
import { useMediaQuery } from "./hooks";

/** Each tool's glyph, by its `icon` in `toolsCollapse`. */
const ICONS = {
  docs: FileTextIcon,
  latex: FunctionIcon,
  careers: BrowsersIcon,
  sites: GlobeSimpleIcon,
  notes: NotePencilIcon,
  clipboard: ClipboardTextIcon,
  sheet: TableIcon,
  calendar: CalendarDotsIcon,
};

/** Where each tool card starts, in `toolsCollapse.tools` order: its left
 *  edge as a share of the row, its top from the frame's top, and its tilt.
 *  One high and one low for each product, so no card
 *  covers another or leaves the frame from 1024 to 1440px (measured: at
 *  30% and 51%, two lower cards overlapped by 14px at 1024). */
const SCATTER = [
  { left: "2%", top: 44, rotate: -6 },
  { left: "6%", top: 300, rotate: 5 },
  { left: "27%", top: 8, rotate: 4 },
  { left: "29%", top: 318, rotate: -4 },
  { left: "54%", top: 28, rotate: -3 },
  { left: "52%", top: 306, rotate: 6 },
  { left: "77%", top: 112, rotate: 5 },
  { left: "75%", top: 316, rotate: -6 },
];

/** The collapse along the pin's scroll, from 0 (the pin starts) to 1 (it
 *  lets go). The cards hold still for the first stretch, so the reader
 *  takes in the scattered tools; then each card flies in turn, its tile
 *  rises as the last of its two cards lands, and the count turns over; the
 *  last stretch rests finished before the page moves on. */
const HOLD = 0.12;
const STAGGER = 0.045;
const FLY = 0.34;
const TILE_RISE = 0.07;
const COUNT_AT = 0.8;
const COUNT_TURN = 0.04;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
/** Ease in and out (a cubic), for the flight. */
const inOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
/** Ease out past the end and back, for a tile settling. */
const outBack = (t: number) => 1 + 2.4 * (t - 1) ** 3 + 1.4 * (t - 1) ** 2;

/**
 * The tools a student juggles, collapsing into WorkIt's four products
 * (KAN-923, after Loopsii's "your whole stack, in one app", the user's
 * pick, 2026-11-20): under "One app for every step of applying", eight
 * tool cards lie scattered on a drafting grid around the four product
 * tiles (`children`, `FeatureJumps`), and as the reader scrolls each pair
 * flies into the product that replaces it and the tiles come up in their
 * place, while the count turns from "8 tools" to "1 app". The end state is
 * the tiles as they are, links and all.
 *
 * **The scroll drives it, and the section pins until it is done** (the
 * user's call, 2026-11-20, the one exception to "Scroll cues, time plays"
 * in frontend/CLAUDE.md): the heading and the frame stay on screen
 * (`.tools-stage`, sticky) while the page scrolls 120svh (`.tools-pin`), and the
 * collapse follows the scroll both ways. Played in time on arrival, it ran
 * before the reader had looked at the scattered tools. The poses are set
 * by script, one per element per scroll frame, as transforms and opacity.
 *
 * From lg up with motion allowed only (`.tools-pin`, `.tools-collapse` in
 * landing.css): on a phone eight cards had no room, and with reduced
 * motion the tiles simply show with no pin. The pin's height is CSS, so
 * the server's HTML has the room; without script the tiles show and the
 * cards stay hidden, and the pinned stretch stands still.
 *
 * Each card flies to the centre of its tile, measured from the layout
 * (offsets ignore transforms), again on every resize. The cards and the
 * count are decoration: the tiles below say the same in words.
 */
export function ToolsCollapse({ heading, children }: { heading: ReactNode; children: ReactNode }) {
  const pinRef = useRef<HTMLDivElement>(null);
  const ref = useRef<HTMLDivElement>(null);
  const live =
    useMediaQuery("(min-width: 64rem) and (prefers-reduced-motion: no-preference)") === true;
  const { scrollYProgress } = useScroll({ target: pinRef, offset: ["start start", "end end"] });

  useEffect(() => {
    const root = ref.current;
    if (!live || !root) return;
    const cards = [...root.querySelectorAll<HTMLElement>("[data-tool]")];
    const tiles = [...root.querySelectorAll<HTMLElement>("[data-tile]")];
    const counts = [...root.querySelectorAll<HTMLElement>(".tools-count > span")];
    // When each tile's last card lands.
    const lands = tiles.map((_, k) =>
      Math.max(
        ...cards.flatMap((card, i) =>
          Number(card.dataset.tool) === k ? [HOLD + i * STAGGER + FLY] : [],
        ),
      ),
    );
    let targets = cards.map(() => ({ x: 0, y: 0 }));

    const pose = (p: number) => {
      cards.forEach((card, i) => {
        const t = clamp01((p - HOLD - i * STAGGER) / FLY);
        const e = inOut(t);
        const { x, y } = targets[i];
        card.style.transform = `translate(${x * e}px, ${y * e}px) rotate(${SCATTER[i].rotate * (1 - e)}deg) scale(${1 - 0.4 * e})`;
        card.style.opacity = String(1 - clamp01((t - 0.7) / 0.3));
      });
      tiles.forEach((tile, k) => {
        const u = clamp01((p - lands[k] + 0.03) / TILE_RISE);
        tile.style.opacity = String(u);
        tile.style.transform = `scale(${0.92 + 0.08 * outBack(u)})`;
      });
      const c = clamp01((p - COUNT_AT) / COUNT_TURN);
      counts.forEach((span, j) => (span.style.opacity = String(j === 0 ? 1 - c : c)));
    };

    const measure = () => {
      targets = cards.map((card) => {
        const tile = tiles[Number(card.dataset.tool)];
        if (!tile) return { x: 0, y: 0 };
        return {
          x: tile.offsetLeft + tile.offsetWidth / 2 - (card.offsetLeft + card.offsetWidth / 2),
          y: tile.offsetTop + tile.offsetHeight / 2 - (card.offsetTop + card.offsetHeight / 2),
        };
      });
      pose(scrollYProgress.get());
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    const stop = scrollYProgress.on("change", pose);
    return () => {
      observer.disconnect();
      stop();
      for (const el of [...cards, ...tiles, ...counts]) {
        el.style.transform = "";
        el.style.opacity = "";
      }
    };
  }, [live, scrollYProgress]);

  return (
    <div ref={pinRef} className="tools-pin">
      <div className="tools-stage">
        {heading}
        <div
          ref={ref}
          data-live={live ? "" : undefined}
          className="tools-collapse relative mt-10 lg:mt-12"
        >
          <div aria-hidden="true" className="tools-frame">
            {/* The shared frame's lines (draft-lines.tsx), so this grid reads
                as the same drawing as every other section's. */}
            <span className="draft-h top-0" />
            <span className="draft-h bottom-0" />
            <span className="draft-v left-0" />
            <span className="draft-v right-0" />
            <i className="top-0 left-0" />
            <i className="top-0 left-full" />
            <i className="top-full left-0" />
            <i className="top-full left-full" />
          </div>
          <p aria-hidden="true" className="tools-count">
            <span className="tools-count-before">{toolsCollapse.before}</span>
            <span className="tools-count-after">{toolsCollapse.after}</span>
          </p>
          {toolsCollapse.tools.map((tool, i) => {
            const Icon = ICONS[tool.icon];
            const at = SCATTER[i];
            return (
              <div
                key={tool.name}
                aria-hidden="true"
                data-tool={tool.tile}
                className="tool-card surface-card w-48 rounded-xl px-3.5 py-3 xl:w-52"
                style={{ left: at.left, top: at.top, "--r": `${at.rotate}deg` } as CSSProperties}
              >
                <span className="flex items-center gap-2.5">
                  <span className="text-ink-meta grid size-7 shrink-0 place-items-center rounded-lg bg-slate-900/[0.05]">
                    <Icon className="size-4" />
                  </span>
                  <span className="text-ink text-[14px] font-medium">{tool.name}</span>
                </span>
                <span className="text-ink-meta mt-1.5 block text-[12.5px] leading-snug">
                  {tool.line}
                </span>
              </div>
            );
          })}
          {children}
        </div>
      </div>
    </div>
  );
}
