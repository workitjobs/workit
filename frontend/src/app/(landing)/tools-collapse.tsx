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

/** Where each tool card starts, in `toolsCollapse.tools` order: the first
 *  of each pair leans on its product's empty slot from above and the
 *  second from below, each `EDGE` from the frame's top or foot so it covers
 *  the slot's edge by about half its height and leaves the slot's mark and
 *  name in view; `nudge` moves it in from its column's left edge, and
 *  `rotate` tilts it. The last top card tilts clockwise, so its right
 *  corner stays clear of the count. */
const SCATTER = [
  { nudge: "0.25rem", rotate: -5 },
  { nudge: "1.75rem", rotate: 4 },
  { nudge: "1.5rem", rotate: 4 },
  { nudge: "0.5rem", rotate: -4 },
  { nudge: "0.5rem", rotate: -3 },
  { nudge: "1.75rem", rotate: 5 },
  { nudge: "0.75rem", rotate: 5 },
  { nudge: "0.25rem", rotate: -5 },
];
const EDGE = "3.25rem";

/** Each tool's screen at its worst moment, by its `icon`: what the student
 *  sees in it, drawn small. Plain UI in slate, the search before WorkIt, as
 *  the problems' scenes are; red marks the trouble. */
const LINE = "block h-1.5 rounded-full bg-slate-900/[0.08]";
const SCREENS: Record<keyof typeof ICONS, ReactNode> = {
  docs: (
    <>
      <span className="text-ink block text-[12px] font-medium">Resume_v7_FINAL (2)</span>
      <span className={`${LINE} mt-2 w-11/12`} />
      <span className={`${LINE} mt-1.5 w-8/12`} />
      <span className={`${LINE} mt-1.5 w-10/12`} />
    </>
  ),
  latex: (
    <span className="block font-mono text-[11px] leading-[1.5]">
      <span className="text-ink-meta block">\section{"{Experience}"}</span>
      <span className="text-danger block">! Overfull \hbox</span>
    </span>
  ),
  careers: (
    <>
      <span className="flex gap-1 text-[11px]">
        {["Stripe", "Notion", "Figma"].map((tab) => (
          <span key={tab} className="text-ink-meta rounded-md border border-slate-900/10 px-1.5">
            {tab}
          </span>
        ))}
        <span className="text-ink-meta">+14</span>
      </span>
      <span className="text-ink-meta mt-1.5 block text-[11px]">Another careers page to check</span>
    </>
  ),
  sites: (
    <span className="text-ink-meta block text-[11px] leading-[1.6]">
      <span className="block">
        <span className="text-ink">Software Intern</span> ·{" "}
        <span className="text-danger">3 months ago</span>
      </span>
      <span className="block">
        <span className="text-ink">Data Intern</span> · 1,204 applicants
      </span>
    </span>
  ),
  notes: (
    <>
      <span className="text-ink block text-[12px] font-medium">Why this company?</span>
      <span className={`${LINE} mt-2 w-10/12`} />
      <span className={`${LINE} mt-1.5 w-6/12`} />
    </>
  ),
  clipboard: (
    <>
      <span className="text-ink-meta flex justify-between text-[11px]">
        Email<span>Pasted again</span>
      </span>
      <span className="text-ink mt-1 block rounded-md border border-slate-900/15 px-1.5 py-0.5 text-[11px]">
        alex@school.edu
      </span>
    </>
  ),
  sheet: (
    <span className="grid grid-cols-2 gap-0.5 text-[11px]">
      <span className="text-ink bg-slate-900/[0.04] px-1.5">Stripe</span>
      <span className="text-ink-meta bg-slate-900/[0.04] px-1.5">Applied</span>
      <span className="text-ink bg-slate-900/[0.04] px-1.5">Figma</span>
      <span className="text-danger bg-danger/10 px-1.5">??</span>
    </span>
  ),
  calendar: (
    <>
      <span className="text-ink-meta block text-[11px]">Thu, 2:00 PM</span>
      <span className="text-ink mt-1 block border-l-2 border-slate-400 bg-slate-900/[0.04] px-1.5 py-0.5 text-[11px]">
        Interview? Which company
      </span>
    </>
  ),
};

/** An element's offset from `root`, summed up its offset parents, so a
 *  tile inside the list and a card on the frame compare in one space
 *  (offsets ignore transforms). */
function offsetIn(el: HTMLElement, root: HTMLElement) {
  let x = 0;
  let y = 0;
  for (
    let at: HTMLElement | null = el;
    at && at !== root;
    at = at.offsetParent as HTMLElement | null
  ) {
    x += at.offsetLeft;
    y += at.offsetTop;
  }
  return { x, y };
}

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
 * pick, 2026-11-20): under "One app for every step of applying", the four
 * products wait as empty slots on a drafting grid (each tile's
 * `data-ghost`: a dashed outline in its colour, its mark and its name;
 * `children`, `FeatureJumps`), and the eight tools they replace lean on
 * them two by two, each card a piece of the tool's own screen at its worst
 * moment (`SCREENS`). As the reader scrolls each pair flies into its slot,
 * the tile fills it, and the count turns from "8 tools" to "1 app". The
 * user picked this over plain cards with a line each, which were boring
 * and hinted at nothing, from three drawn options (2026-11-20). The end
 * state is the tiles as they are, links and all.
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
    const bodies = tiles.map((tile) => tile.querySelector<HTMLElement>("[data-tile-body]"));
    const ghosts = tiles.map((tile) => tile.querySelector<HTMLElement>("[data-ghost]"));
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
        card.style.transform = `translate(${x * e}px, ${y * e}px) rotate(${SCATTER[i].rotate * (1 - e)}deg) scale(${1 - 0.45 * e})`;
        card.style.opacity = String(1 - clamp01((t - 0.7) / 0.3));
      });
      tiles.forEach((_, k) => {
        const u = clamp01((p - lands[k] + 0.03) / TILE_RISE);
        const body = bodies[k];
        if (body) {
          body.style.opacity = String(u);
          body.style.transform = `scale(${0.92 + 0.08 * outBack(u)})`;
        }
        const ghost = ghosts[k];
        if (ghost) ghost.style.opacity = String(1 - u);
      });
      const c = clamp01((p - COUNT_AT) / COUNT_TURN);
      counts.forEach((span, j) => (span.style.opacity = String(j === 0 ? 1 - c : c)));
    };

    const measure = () => {
      targets = cards.map((card) => {
        const tile = tiles[Number(card.dataset.tool)];
        if (!tile) return { x: 0, y: 0 };
        const t = offsetIn(tile, root);
        const c = offsetIn(card, root);
        return {
          x: t.x + tile.offsetWidth / 2 - (c.x + card.offsetWidth / 2),
          y: t.y + tile.offsetHeight / 2 - (c.y + card.offsetHeight / 2),
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
      for (const el of [...cards, ...bodies, ...ghosts, ...counts]) {
        if (!el) continue;
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
                className="tool-card surface-card w-48 overflow-hidden rounded-xl xl:w-52"
                style={
                  {
                    left: `calc(${tool.tile * 25}% + ${at.nudge})`,
                    [i % 2 === 0 ? "top" : "bottom"]: EDGE,
                    "--r": `${at.rotate}deg`,
                  } as CSSProperties
                }
              >
                {/* The tool's own bar, then its screen. */}
                <span className="text-ink-meta flex items-center gap-1.5 border-b border-slate-900/[0.06] px-3 py-1.5 text-[11.5px] font-medium">
                  <Icon className="size-3.5" />
                  {tool.name}
                </span>
                <span className="block px-3 py-2.5">{SCREENS[tool.icon]}</span>
              </div>
            );
          })}
          {children}
        </div>
      </div>
    </div>
  );
}
