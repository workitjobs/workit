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
/** How long the whole snake takes, out of the hero or back into it, ms. */
const RUN = 2400;
/** The feed's beat once the snake has gone: one step a beat, ms. */
const BEAT = 1100;
/** Scrolled past this, the snake leaves; back within `HOME`, it returns. */
const AWAY = 32;
const HOME = 8;

/**
 * The hero flowing into the job feed (KAN-923, the user's idea, built
 * 2026-11-20, after the game Snake): the ring of glass tiles round the
 * headline unzips at its bottom-left corner into one snake that steps
 * down the grid, turns right along the feed's row under the hero and is
 * eaten, tile by tile, by a white WorkIt cell at the row's end, so by the
 * time the reader reaches the feed the hero's frame is empty. The tiles
 * turn violet once they leave the hero and become company logo tiles on
 * the row; the hero's violet ground fades as it empties (`.hero-fade`).
 * Then the row keeps feeding WorkIt: a logo tile enters every other beat
 * and steps one cell a beat into it. It replaced the logo strip's drifting
 * names, which the user found generic (`logo-strip.tsx`, unmounted).
 *
 * **The scroll cues, time plays** (frontend/CLAUDE.md): the first scroll
 * away from the top sends the snake, which plays to its end in `RUN`;
 * back at the top it plays backwards out of WorkIt into the ring. Never
 * scrubbed, so it never rests half way. Nothing pins.
 *
 * **How it moves**: the hero's own tiles stay put and hide while the
 * snake runs (`data-snake`); copies of them (`.snake-tile`, no backdrop
 * blur, which twenty-eight moving tiles could not afford) start on their
 * cells and move along one path of cell boxes: the ring from its tail to
 * its head (bottom row, up the right side, the top row back, down the left
 * side), the feed's drop cell, the row's cells and WorkIt's. At step `t`
 * a tile `k` stands at `min(k + t, end)`, so each follows the one ahead
 * cell for cell, as Snake's body does. Every box is measured from the
 * layout, again on each resize at rest, so the path fits the hero's 7, 9
 * or 11 columns, and the feed's row shares its columns (`.feed-grid`).
 *
 * From lg up only (below it the hero has no ring); a phone gets the feed's
 * row alone. With reduced motion, and before the script runs, the row
 * shows its logos at rest and the hero stays whole (`data-live` unset).
 * The loop rests off screen and in a hidden tab.
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

    const clones = [...root.querySelectorAll<HTMLElement>("[data-clone]")];
    const feeders = [...root.querySelectorAll<HTMLElement>("[data-feeder]")];
    const wk = root.querySelector<HTMLElement>("[data-feed-wk]")!;

    type Geo = { path: Box[]; ring: number; size: Box; row: Box[] };
    let geo: Geo | null = null;
    let phase: "rest" | "running" | "done" | "reversing" = "rest";
    let snakeTimer = 0;
    let feedTimer = 0;
    let t = 0;
    let visible = false;
    let beat = 0;
    let nextFeeder = 0;
    const active: { el: HTMLElement; i: number }[] = [];
    // Below lg: the feed's row alone, no snake.
    let rowOnly: Box[] | null = null;

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

    function measure(): Geo | null {
      const base = root!.getBoundingClientRect();
      const cells = (selector: string) =>
        [...root!.querySelectorAll<HTMLElement>(selector)].filter(
          (el) => getComputedStyle(el).display !== "none",
        );
      const row = cells("[data-feed-cell]").map((el) => boxOf(el, base));
      const drop = root!.querySelector("[data-feed-drop]");
      if (!drop) return null;
      const end = boxOf(wk, base);
      const tiles = cells(".hero-tile").map((el) => boxOf(el, base));
      const rowOf = bands(tiles.map((b) => b.y));
      const colOf = bands(tiles.map((b) => b.x));
      const at = new Map(tiles.map((b) => [`${rowOf(b.y)},${colOf(b.x)}`, b]));
      const R = Math.max(...tiles.map((b) => rowOf(b.y))) + 1;
      const C = Math.max(...tiles.map((b) => colOf(b.x))) + 1;
      const ring: Box[] = [];
      for (let c = 1; c < C; c++) ring.push(at.get(`${R - 1},${c}`)!);
      for (let r = R - 2; r >= 1; r--) ring.push(at.get(`${r},${C - 1}`)!);
      for (let c = C - 1; c >= 0; c--) ring.push(at.get(`0,${c}`)!);
      for (let r = 1; r < R; r++) ring.push(at.get(`${r},0`)!);
      // A ring only from lg up, with every cell found.
      if (R < 3 || ring.some((b) => !b) || ring.length !== tiles.length) return null;
      return {
        path: [...ring, boxOf(drop, base), ...row, end],
        ring: ring.length,
        size: ring[ring.length - 1],
        row: [...row, end],
      };
    }

    const look = (i: number, g: Geo) =>
      i < g.ring ? "glass" : i === g.ring ? "out" : i >= g.path.length - 1 ? "eaten" : "logo";

    function place(el: HTMLElement, box: Box, size: Box, eaten: boolean) {
      const sx = box.w / size.w;
      const sy = box.h / size.h;
      const shrink = eaten ? 0.45 : 1;
      el.style.transform = `translate(${box.x + (box.w * (1 - shrink)) / 2}px, ${
        box.y + (box.h * (1 - shrink)) / 2
      }px) scale(${sx * shrink}, ${sy * shrink})`;
    }

    function setSnake(step: number, animate: boolean) {
      if (!geo) return;
      const g = geo;
      const end = g.path.length - 1;
      clones.forEach((el, k) => {
        if (k >= g.ring) {
          el.dataset.look = "off";
          return;
        }
        const i = Math.min(k + step, end);
        if (!animate) el.style.transitionDuration = "0ms";
        el.style.width = `${g.size.w}px`;
        el.style.height = `${g.size.h}px`;
        el.dataset.look = look(i, g);
        place(el, g.path[i], g.size, i === end);
      });
    }

    function gulp() {
      wk.removeAttribute("data-gulp");
      void wk.offsetWidth;
      wk.setAttribute("data-gulp", "");
    }

    function snakeOn() {
      return lg.matches && geo !== null;
    }

    function run(forward: boolean) {
      if (!geo) return;
      const g = geo;
      const steps = g.path.length - 1;
      const step = Math.min(110, Math.max(55, RUN / steps));
      clearInterval(snakeTimer);
      stopFeed();
      hideFeeders();
      phase = forward ? "running" : "reversing";
      root!.dataset.snake = "";
      root!.style.setProperty("--run", `${RUN}ms`);
      if (forward) root!.dataset.ground = "faded";
      else delete root!.dataset.ground;
      clones.forEach((el) => (el.style.transitionDuration = "0ms"));
      setSnake(forward ? 0 : steps, false);
      void root!.offsetWidth;
      clones.forEach((el) => (el.style.transitionDuration = `${step}ms`));
      t = forward ? 0 : steps;
      snakeTimer = window.setInterval(() => {
        t += forward ? 1 : -1;
        setSnake(t, true);
        if (forward && t <= steps) {
          const eatenNow = clones.filter((_, k) => k < g.ring && k + t === steps).length;
          if (eatenNow) gulp();
        }
        if ((forward && t >= steps) || (!forward && t <= 0)) {
          clearInterval(snakeTimer);
          if (forward) {
            phase = "done";
            syncFeed();
            if (window.scrollY <= HOME) run(false);
          } else {
            phase = "rest";
            delete root!.dataset.snake;
            clones.forEach((el) => (el.dataset.look = "off"));
            if (window.scrollY > AWAY) run(true);
          }
        }
      }, step);
    }

    // The feed's loop: a logo tile enters every other beat and steps one
    // cell a beat into WorkIt.
    function feedStep() {
      if (!geo && !rowOnly) return;
      const row = geo ? geo.row : rowOnly!;
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
        place(f.el, row[f.i], size, f.i >= end);
        if (f.i >= end) window.setTimeout(gulp, BEAT / 2);
      }
      if (beat % 2 === 0) {
        const el = feeders[nextFeeder % feeders.length];
        nextFeeder++;
        if (!active.some((f) => f.el === el)) {
          el.style.transitionDuration = "0ms";
          el.style.width = `${size.w}px`;
          el.style.height = `${size.h}px`;
          place(el, row[0], size, false);
          el.dataset.look = "enter";
          void el.offsetWidth;
          el.style.transitionDuration = "";
          el.dataset.look = "logo";
          active.push({ el, i: 0 });
        }
      }
      beat++;
    }
    function stopFeed() {
      clearInterval(feedTimer);
      feedTimer = 0;
    }
    function hideFeeders() {
      active.splice(0).forEach((f) => (f.el.dataset.look = "off"));
    }
    function syncFeed() {
      const wanted =
        visible && !document.hidden && (snakeOn() ? phase === "done" : rowOnly !== null);
      if (wanted && !feedTimer) {
        feedStep();
        feedTimer = window.setInterval(feedStep, BEAT);
      } else if (!wanted) stopFeed();
    }

    function measureRow() {
      const base = root!.getBoundingClientRect();
      const cells = [...root!.querySelectorAll<HTMLElement>("[data-feed-cell]")].filter(
        (el) => getComputedStyle(el).display !== "none",
      );
      return [...cells.map((el) => boxOf(el, base)), boxOf(wk, base)];
    }

    function layout() {
      geo = lg.matches ? measure() : null;
      rowOnly = geo ? null : measureRow();
      if (!geo) {
        // No snake: the hero stays whole.
        clearInterval(snakeTimer);
        phase = "rest";
        delete root!.dataset.snake;
        delete root!.dataset.ground;
        clones.forEach((el) => (el.dataset.look = "off"));
      } else if (phase === "done") setSnake(geo.path.length - 1, false);
    }

    layout();
    // Arriving already scrolled (a return, an anchor): the snake has gone.
    if (snakeOn() && window.scrollY > AWAY) {
      phase = "done";
      root.dataset.snake = "";
      root.dataset.ground = "faded";
      root.style.setProperty("--run", "0ms");
      setSnake(geo!.path.length - 1, false);
    }

    const onScroll = () => {
      if (!snakeOn()) return;
      const y = window.scrollY;
      if (y > AWAY && phase === "rest") run(true);
      else if (y <= HOME && phase === "done") run(false);
    };
    const onResize = () => {
      if (phase === "running" || phase === "reversing") return;
      layout();
      hideFeeders();
      syncFeed();
    };
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
      clearInterval(snakeTimer);
      stopFeed();
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
