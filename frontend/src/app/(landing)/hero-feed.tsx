"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { Logo } from "@/components/logo";

import { FaviconLogo } from "./favicon-logo";
import { PANEL_INSET, TYPE } from "./layout-parts";

type Employer = { name: string; domain: string };
type Box = { x: number; y: number; w: number; h: number };

/** The most hero tiles any layout shows (11 columns, hero-board.tsx). */
const MAX_TILES = 28;
/** The most track cells the feed's row shows: 11 columns, less WorkIt's. */
const TRACK = 10;
/** How far down the page, as a share of the hero's height, the snake has
 *  wholly left the hero: the hero's full height, so it lands as the hero
 *  scrolls away (at 85% it ran about four cells a wheel notch). */
const RANGE = 1;
/** The feed's beat once the snake is in: every logo steps one cell, ms. */
const BEAT = 1800;

/**
 * The hero flowing into the job feed (KAN-923, the user's idea, after the
 * game Snake, 2026-11-20): the whole frame turns into one snake. The ring
 * of glass tiles round the headline unzips at its bottom-left corner and
 * steps down the grid, turns right along the feed's row under the hero,
 * and the head is eaten by a white WorkIt cell at the row's end, while the
 * headline's tile and the violet ground fade out, so by the time the
 * reader reaches the feed nothing is left of the hero (the user's words).
 * The tiles turn violet once out of the hero and become company logo tiles
 * on the row. When the snake is in, the row lies full, logo against logo,
 * and keeps feeding WorkIt on its own: every `BEAT` each logo steps one
 * cell, the one at the end goes into WorkIt and a new one enters at the
 * start, so no cell is ever empty between two (the user's catch: one
 * entering every other beat left a gap between each). It replaced the logo
 * strip's drifting names, which the user found generic (`logo-strip.tsx`,
 * unmounted).
 *
 * **The scroll drives it**, the user's call over a timer, which ran the
 * snake far quicker than anyone scrolls: it is as far along as the page is
 * down the first `RANGE` of the hero's height, out on the way down and
 * back in on the way up, and rests where the reader stops. A tile moves
 * along the grid between neighbouring cells, never on a curve.
 *
 * **How it moves**: the hero's own tiles stay put and hide once the page
 * leaves the top (`data-snake`); copies of them (`.snake-tile`, with no
 * backdrop blur, which twenty-eight moving tiles could not afford) move
 * along one path of cell boxes: the ring from its tail to its head (bottom
 * row, up the right side, the top row back, down the left side), the feed's
 * drop cell, the row's cells and WorkIt's. At step `s` a tile `k` stands at
 * `k + s`, so each follows the one ahead cell for cell, as Snake's body
 * does; `s` runs from 0 to the ring's length plus one, where the tail has
 * reached the row's first cell and the row is full. Every box is measured
 * from the layout, again on each resize, so the path fits the hero's 7, 9
 * or 11 columns, and the feed's row shares its columns (`.feed-grid`).
 * Transforms and two custom properties (`--snake-p` for the fades), set
 * once a frame while the page scrolls.
 *
 * From lg up only (below it the hero has no ring); a phone gets the feed's
 * row alone, full and stepping. With reduced motion, and before the script
 * runs, the row shows its logos at rest and the hero stays whole
 * (`data-live` unset). The feed rests off screen and in a hidden tab.
 */
export function HeroFeed({
  children,
  line,
  employers,
}: {
  /** The hero's section, drawn by the server. */
  children: ReactNode;
  line: string;
  employers: readonly Employer[];
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const feedRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    const feed = feedRef.current;
    if (!root || !feed) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lg = window.matchMedia("(min-width: 64rem)");
    root.dataset.live = "";

    const hero = root.firstElementChild as HTMLElement;
    const clones = [...root.querySelectorAll<HTMLElement>("[data-clone]")];
    const feeders = [...root.querySelectorAll<HTMLElement>("[data-feeder]")];
    const wk = root.querySelector<HTMLElement>("[data-feed-wk]")!;

    type Geo = { path: Box[]; ring: number; size: Box };
    let geo: Geo | null = null;
    /** The row's cells and WorkIt's, last. */
    let row: Box[] = [];
    let range = 1;
    let raf = 0;
    let lastEaten = 0;
    let visible = false;
    let feedTimer = 0;
    let nextFeeder = 0;
    let snakeIn = false;
    const active: { el: HTMLElement; i: number }[] = [];

    const boxOf = (el: Element, base: DOMRect): Box => {
      const r = el.getBoundingClientRect();
      return { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
    };
    /** Groups near-equal positions (sub-pixel layout) into rows or columns. */
    const bands = (values: number[]) => {
      const sorted = [...values].sort((a, b) => a - b);
      const out: number[] = [];
      for (const v of sorted) if (!out.length || v - out[out.length - 1] > 4) out.push(v);
      return (v: number) => out.findIndex((o) => Math.abs(o - v) <= 4);
    };
    const shown = (selector: string) =>
      [...root!.querySelectorAll<HTMLElement>(selector)].filter(
        (el) => getComputedStyle(el).display !== "none",
      );

    function measure() {
      const base = root!.getBoundingClientRect();
      row = [...shown("[data-feed-cell]").map((el) => boxOf(el, base)), boxOf(wk, base)];
      range = Math.max(1, hero.offsetHeight * RANGE);
      geo = null;
      if (!lg.matches) return;
      const drop = root!.querySelector("[data-feed-drop]");
      const tiles = shown(".hero-tile").map((el) => boxOf(el, base));
      if (!drop || !tiles.length) return;
      const rowOf = bands(tiles.map((b) => b.y));
      const colOf = bands(tiles.map((b) => b.x));
      const at = new Map(tiles.map((b) => [`${rowOf(b.y)},${colOf(b.x)}`, b]));
      const R = Math.max(...tiles.map((b) => rowOf(b.y))) + 1;
      const C = Math.max(...tiles.map((b) => colOf(b.x))) + 1;
      const ring: (Box | undefined)[] = [];
      for (let c = 1; c < C; c++) ring.push(at.get(`${R - 1},${c}`));
      for (let r = R - 2; r >= 1; r--) ring.push(at.get(`${r},${C - 1}`));
      for (let c = C - 1; c >= 0; c--) ring.push(at.get(`0,${c}`));
      for (let r = 1; r < R; r++) ring.push(at.get(`${r},0`));
      // A ring only from lg up, with every cell found.
      if (R < 3 || ring.some((b) => !b) || ring.length !== tiles.length) return;
      const cells = ring as Box[];
      geo = {
        path: [...cells, boxOf(drop, base), ...row],
        ring: cells.length,
        size: cells[cells.length - 1],
      };
    }

    const look = (i: number, g: Geo) => (i < g.ring ? "glass" : i === g.ring ? "out" : "logo");

    function place(el: HTMLElement, box: Box, size: Box, shrink = 1) {
      el.style.transform = `translate(${box.x + (box.w * (1 - shrink)) / 2}px, ${
        box.y + (box.h * (1 - shrink)) / 2
      }px) scale(${(box.w / size.w) * shrink}, ${(box.h / size.h) * shrink})`;
    }
    const lerp = (a: Box, b: Box, f: number): Box => ({
      x: a.x + (b.x - a.x) * f,
      y: a.y + (b.y - a.y) * f,
      w: a.w + (b.w - a.w) * f,
      h: a.h + (b.h - a.h) * f,
    });

    function gulp() {
      wk.removeAttribute("data-gulp");
      void wk.offsetWidth;
      wk.setAttribute("data-gulp", "");
    }

    // The snake, as far along as the page is down.
    function render() {
      raf = 0;
      if (!geo) return syncFeed();
      const g = geo;
      const p = Math.min(1, Math.max(0, window.scrollY / range));
      root!.style.setProperty("--snake-p", p.toFixed(3));
      if (p <= 0) {
        delete root!.dataset.snake;
        root!.removeAttribute("data-hero-gone");
        clones.forEach((el) => (el.dataset.look = "off"));
        lastEaten = 0;
        leaveFeed();
        return;
      }
      root!.dataset.snake = "";
      // The headline's buttons stop taking clicks once it has mostly gone.
      root!.toggleAttribute("data-hero-gone", p > 0.6);
      if (p >= 1) {
        // The tail has reached the row's first cell: the feed takes over.
        clones.forEach((el) => (el.dataset.look = "off"));
        if (!snakeIn) enterFeed();
        return;
      }
      leaveFeed();
      const last = g.path.length - 1;
      const step = p * (g.ring + 1);
      clones.forEach((el, k) => {
        if (k >= g.ring) return void (el.dataset.look = "off");
        const at = k + step;
        if (at >= last) return void (el.dataset.look = "eaten");
        const i = Math.floor(at);
        const f = at - i;
        // The last cell's step shrinks the tile into WorkIt.
        const shrink = i + 1 === last ? 1 - 0.55 * f : 1;
        el.style.width = `${g.size.w}px`;
        el.style.height = `${g.size.h}px`;
        el.dataset.look = look(f > 0.5 ? i + 1 : i, g);
        place(el, lerp(g.path[i], g.path[i + 1], f), g.size, shrink);
      });
      // WorkIt pulses as each tile goes in.
      const eaten = Math.max(0, Math.min(g.ring, Math.floor(g.ring + step - last)));
      if (eaten > lastEaten) gulp();
      lastEaten = eaten;
    }

    // The feed: the row full, each logo a cell along every beat.
    function fill() {
      active.splice(0).forEach((f) => (f.el.dataset.look = "off"));
      const size = row[0];
      const n = row.length - 1;
      for (let j = 0; j < n; j++) {
        const el = feeders[j % feeders.length];
        el.style.transitionDuration = "0ms";
        el.style.width = `${size.w}px`;
        el.style.height = `${size.h}px`;
        place(el, row[j], size);
        el.dataset.look = "logo";
        active.push({ el, i: j });
      }
      nextFeeder = n;
      void root!.offsetWidth;
      active.forEach((f) => (f.el.style.transitionDuration = ""));
    }
    function feedStep() {
      const size = row[0];
      const end = row.length - 1;
      for (let a = active.length - 1; a >= 0; a--) {
        const f = active[a];
        if (f.i >= end) {
          f.el.dataset.look = "off";
          active.splice(a, 1);
          continue;
        }
        f.i++;
        f.el.dataset.look = f.i >= end ? "eaten" : "logo";
        place(f.el, row[f.i], size, f.i >= end ? 0.45 : 1);
        if (f.i >= end) window.setTimeout(gulp, BEAT * 0.4);
      }
      // A new logo into the first cell, which the step just emptied.
      let el = feeders[nextFeeder % feeders.length];
      for (let tries = 0; active.some((f) => f.el === el) && tries < feeders.length; tries++) {
        nextFeeder++;
        el = feeders[nextFeeder % feeders.length];
      }
      nextFeeder++;
      el.style.transitionDuration = "0ms";
      el.style.width = `${size.w}px`;
      el.style.height = `${size.h}px`;
      place(el, row[0], size);
      el.dataset.look = "enter";
      void el.offsetWidth;
      el.style.transitionDuration = "";
      el.dataset.look = "logo";
      active.push({ el, i: 0 });
    }
    function enterFeed() {
      snakeIn = true;
      fill();
      syncFeed();
    }
    function leaveFeed() {
      if (!snakeIn) return;
      snakeIn = false;
      clearInterval(feedTimer);
      feedTimer = 0;
      active.splice(0).forEach((f) => (f.el.dataset.look = "off"));
    }
    function syncFeed() {
      // Below lg the feed runs alone; from lg up once the snake is in.
      if (!geo && !active.length && row.length) fill();
      const wanted = visible && !document.hidden && (geo ? snakeIn : true);
      if (wanted && !feedTimer) feedTimer = window.setInterval(feedStep, BEAT);
      else if (!wanted && feedTimer) {
        clearInterval(feedTimer);
        feedTimer = 0;
      }
    }

    function layout() {
      measure();
      if (!geo) {
        delete root!.dataset.snake;
        clones.forEach((el) => (el.dataset.look = "off"));
        root!.style.removeProperty("--snake-p");
        snakeIn = false;
        fill();
        syncFeed();
      } else {
        if (snakeIn) fill();
        render();
      }
    }
    layout();

    const onScroll = () => {
      if (geo && !raf) raf = requestAnimationFrame(render);
    };
    const onResize = () => layout();
    const seen = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      syncFeed();
    });
    seen.observe(feed);
    const onVisibility = () => syncFeed();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(feedTimer);
      seen.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <div ref={rootRef} className="hero-feed relative">
      {children}

      {/* The job feed under the hero, on the hero's columns: a drop cell
          under the hero's bottom-left tile beside the line, then a row of
          track cells ending in WorkIt's cell. */}
      <section ref={feedRef} aria-labelledby="feed-line" className={PANEL_INSET}>
        <div className="p-2 sm:p-3">
          <div className="feed-grid">
            <div aria-hidden="true" data-feed-drop className="feed-cell" />
            <p
              id="feed-line"
              className={`${TYPE.eyebrow} text-ink-meta self-center px-2 sm:px-4`}
              style={{ gridColumn: "2 / -1" }}
            >
              {line}
            </p>
            <div className="feed-row">
              {Array.from({ length: TRACK }, (_, i) => (
                <div key={i} aria-hidden="true" data-feed-cell className="feed-cell">
                  {/* At rest (no script, reduced motion) each cell holds a
                      logo; the live feed hides them (`data-live`). */}
                  <FeedLogo employer={employers[i % employers.length]} className="feed-static" />
                </div>
              ))}
              <div aria-hidden="true" data-feed-wk className="feed-wk">
                <Logo size="mark" decorative className="h-9 lg:h-11" />
              </div>
            </div>
          </div>
          <ul className="sr-only">
            {employers.map((employer) => (
              <li key={employer.domain}>{employer.name}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* The snake: copies of the hero's tiles, placed by the script. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-10">
        {Array.from({ length: MAX_TILES }, (_, k) => (
          <div key={k} data-clone data-look="off" className="snake-tile">
            <FeedLogo employer={employers[k % employers.length]} className="snake-logo" />
          </div>
        ))}
        {employers.map((employer) => (
          <div key={employer.domain} data-feeder data-look="off" className="snake-tile feeder">
            <FeedLogo employer={employer} className="snake-logo" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** A company's logo tile on the feed: its favicon and, from lg up, its name. */
function FeedLogo({ employer, className }: { employer: Employer; className?: string }) {
  return (
    <span className={`feed-logo ${className ?? ""}`}>
      <FaviconLogo domain={employer.domain} eager className="size-8 rounded-lg lg:size-10" />
      <span className="text-ink hidden truncate text-xs font-medium lg:block">{employer.name}</span>
    </span>
  );
}
