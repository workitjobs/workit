"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

import { MatchGlyph } from "@/components/match-badge";
import { cn } from "@/lib/cn";
import { matchTier } from "@/lib/match";

import {
  buildCity,
  STRIP_HEIGHT,
  STRIP_TOP,
  STRIP_WIDTH,
  type City,
  type Piece,
} from "./city-model";
import { FaviconLogo } from "./favicon-logo";
import { useMediaQuery } from "./hooks";
import { MESH } from "./layout-parts";

// Below Tailwind's sm a phone gets its own, larger city (city-model.ts,
// buildCity's `phone`, and the width in landing.css).
const PHONE_QUERY = "(width < 40rem)";

// Each build once per page load: the model is deterministic, so every
// render draws the same city.
const cached = new Map<boolean, City>();
const getCity = (phone: boolean) => {
  let city = cached.get(phone);
  if (!city) cached.set(phone, (city = buildCity({ phone })));
  return city;
};

const vars = (values: Record<string, string | number>) => values as CSSProperties;

const VIEW_BOX = `0 ${STRIP_TOP} ${STRIP_WIDTH} ${STRIP_HEIGHT}`;

/**
 * The buildings' look (redrawn 2026-11-23 for the page's paper and ink):
 * white tops, two cool greys for the faces and slate hairlines for the
 * edges, the drafting grid's own line, so the city reads as a drawing on
 * the page and the coloured towers are its only colour. It was lit in
 * violet-tinted greys with violet edges, from the page before KAN-923. The
 * window grids and cross-hatching stay a hint (`--floor`, `--pier`): at
 * full weight on every face the buildings ran together (KAN-540). One
 * source for the still images, which landing.css cannot reach (an image is
 * a document of its own). Every tone is one temperature, a cool slate: a
 * warm grey beside it read as dirt.
 */
const LOOK: [selector: string, rules: string][] = [
  [
    "",
    "--top:#fff;--left:#e6e9ee;--right:#f4f5f8;--edge:rgb(15 23 42/.26);--hi:rgb(15 23 42/.1);--floor:rgb(15 23 42/.045);--pier:rgb(15 23 42/.06);--spire:#b9bfca",
  ],
  [".tone-stone", "--left:#eaecf0;--right:#f6f7f9"],
  [".tone-peri", "--left:#e1e5ec;--right:#f1f3f7"],
  [".tone-glass", "--top:#fbfcfd;--left:#dfe3ea;--right:#eff1f5"],
  [".tone-deep", "--top:#f9fafb;--left:#dde1e8;--right:#eceef3"],
  [".t", "fill:var(--top)"],
  [".l", "fill:var(--left)"],
  [".r", "fill:var(--right)"],
  [".fl", "fill:none;stroke:var(--floor);stroke-width:.8"],
  [".pi", "fill:none;stroke:var(--pier);stroke-width:1"],
  [".e", "fill:none;stroke:var(--edge);stroke-width:.9;stroke-linejoin:round"],
  [".hi", "fill:none;stroke:var(--hi);stroke-width:1"],
  [".sp", "fill:none;stroke:var(--spire);stroke-width:1.3;stroke-linecap:round"],
];
const LOOK_CSS = LOOK.map(
  ([selector, rules]) => `svg${selector ? ` ${selector}` : ""}{${rules}}`,
).join("");

/** A building's solid parts, back to front. */
const SOLID = ["l", "r", "t", "fl", "pi", "e", "hi", "sp"] as const;

/** Still pieces as one SVG document, for an image. */
function stillSvg(pieces: Piece[]) {
  const body = pieces
    .map(
      (piece) =>
        `<g class="tone-${piece.tone}">${SOLID.map((part) =>
          piece[part] ? `<path class="${part}" d="${piece[part]}"/>` : "",
        ).join("")}${
          // Distance haze on the back rows (`op`), as a wash of the page's
          // white over the piece, which stays solid. As the piece's own
          // opacity (until 2026-11-23), every building behind showed
          // through it, lines and all, and a coloured tower tinted the
          // buildings in front of it.
          piece.op < 1
            ? `<path d="${piece.l}${piece.r}${piece.t}" fill="#fff" opacity="${(1 - piece.op).toFixed(2)}"/>`
            : ""
        }</g>`,
    )
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${VIEW_BOX}"><style>${LOOK_CSS}</style>${body}</svg>`;
}

/**
 * A tower's colours: one of the four feature colours (`MESH` in
 * layout-parts.tsx, the blends every `StudioBox` uses), so the hero's only
 * colour is the page's own four. Its faces run from the feature's lower
 * neighbour hue at the foot to its upper one at the roof, as a box's ground
 * does, at `STRENGTH` over white: stronger than a box's 46%, since a tower
 * is a few hundred square px on a white page where a box is a whole panel.
 */
const STRENGTH = 0.72;
const HUES = [
  "var(--color-advanced)",
  "var(--color-matching)",
  "var(--color-positive)",
  "var(--color-updates)",
] as const;
/** Each tower's colour, by its turn in the loop: about three towers stand
 *  at a time, one turn after another, and in this order no three turns in
 *  a row share a colour, round the loop's end too. In draw order two blue
 *  towers stood at once, either side of the headline. */
const TURN_HUES = [0, 1, 2, 3, 1, 2];
/** A tower's turn in the loop, 0 to 5, from the model's `delay` (2.7s a
 *  turn). landing.css starts each tower's loop by it (`--turn`), counted
 *  from the city's arrival, so no tower is up while the city comes in. */
const turnOf = (delay: string) => Math.round(-parseFloat(delay) / 2.7);
const INK = "#121a28";
const mix = (hex: string, into: string, share: number) => {
  const channel = (color: string, i: number) => parseInt(color.slice(1 + i * 2, 3 + i * 2), 16);
  return `#${[0, 1, 2]
    .map((i) =>
      Math.round(channel(hex, i) * share + channel(into, i) * (1 - share))
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
};
const TOWER_COLOURS = HUES.map((hue) => {
  const [ground, low, high, light] = MESH[hue];
  const tone = (color: string) => mix(color, "#ffffff", STRENGTH);
  return {
    low: tone(low),
    ground: tone(ground),
    high: tone(high),
    roof: mix(light, "#ffffff", 0.9),
    edge: mix(ground, INK, 0.62),
  };
});

/** The box a piece's paths fill, in the strip's units: every number in
 *  the model's path data is an absolute x or y, in turn. */
function boundsOf(piece: Piece) {
  const numbers = `${piece.gl} ${piece.gr} ${piece.gt} ${piece.we}`.match(/-?\d+(\.\d+)?/g) ?? [];
  let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
  numbers.forEach((text, i) => {
    const n = Number(text);
    if (i % 2 === 0) {
      x0 = Math.min(x0, n);
      x1 = Math.max(x1, n);
    } else {
      y0 = Math.min(y0, n);
      y1 = Math.max(y1, n);
    }
  });
  // Room for the edges' stroke.
  const PAD = 2;
  return { x: x0 - PAD, y: y0 - PAD, w: x1 - x0 + PAD * 2, h: y1 - y0 + PAD * 2 };
}

/**
 * The city as layers, back to front: runs of still pieces, each drawn as
 * one image, and between them the coloured towers, each an SVG of its own.
 * Split where the towers fall in the draw order, so every building in
 * front of a tower stays in front. One SVG of some 5,700 paths made every
 * repaint of the page slow (Chrome re-layers the page's whole paint each
 * frame, about 12ms on an M1 while the city was within reach of the
 * screen); an image is one item to it, whatever it draws (KAN-368). Blob
 * URLs, made once per build and kept for the page's life, like the build.
 *
 * A tower is its own small SVG, the size of its box, so its rise is a
 * transform on an HTML box, which the browser runs off the main thread.
 * As groups inside one strip-sized SVG (until 2026-11-23) each rise
 * repainted that SVG on the main thread, for the whole loop.
 */
type Tower = { piece: Piece; index: number; hue: number };
type Layer = { still: string } | { towers: Tower[] };
const layersCache = new Map<boolean, Layer[]>();
function getLayers(phone: boolean) {
  const known = layersCache.get(phone);
  if (known) return known;
  const layers: Layer[] = [];
  let still: Piece[] = [];
  let towers: Tower[] = [];
  const flush = () => {
    if (still.length) {
      const blob = new Blob([stillSvg(still)], { type: "image/svg+xml" });
      layers.push({ still: URL.createObjectURL(blob) });
    }
    if (towers.length) layers.push({ towers });
    still = [];
    towers = [];
  };
  getCity(phone).pieces.forEach((piece, index) => {
    if (piece.mode) {
      if (still.length) flush();
      // Its colour, by its turn in the loop.
      towers.push({ piece, index, hue: TURN_HUES[turnOf(piece.delay) % TURN_HUES.length] });
    } else {
      if (towers.length) flush();
      still.push(piece);
    }
  });
  flush();
  layersCache.set(phone, layers);
  return layers;
}

/** Room kept between a job card and the panel's sides, and the text. */
const EDGE = 16;
const TEXT_GAP = 10;

/**
 * Where each job card can show: its horizontal nudge in px to stay inside
 * the panel, or null when it cannot fit (its tower is cropped off, or the
 * card would cover the text). Measured in the browser, since what fits
 * depends on the window: the strip keeps its 1600px scale from lg up and is
 * cropped at the sides, while the text keeps its own size. The text is the
 * panel's [data-hero-text] line boxes and its [data-hero-box]'s buttons
 * and links.
 */
function placeCards(root: HTMLElement, panel: HTMLElement) {
  const pr = panel.getBoundingClientRect();
  const cr = root.getBoundingClientRect();
  const text: DOMRect[] = [];
  // Each run of text on its own: a block child's box spans the full width,
  // which once hid every card beside the headline.
  panel.querySelectorAll<HTMLElement>("[data-hero-text]").forEach((el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.textContent?.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      text.push(...Array.from(range.getClientRects()));
    }
  });
  // The buttons and links themselves: the box's own children are
  // `display: contents` wrappers (`SessionSwap`), which have no box.
  panel.querySelectorAll<HTMLElement>("[data-hero-box] :is(a, button)").forEach((el) => {
    const box = el.getBoundingClientRect();
    if (box.width > 0) text.push(box);
  });

  const placement: Record<string, number | null> = {};
  root.querySelectorAll<HTMLElement>("[data-tag]").forEach((el) => {
    const card = el.querySelector<HTMLElement>("[data-card]");
    const company = el.dataset.tag;
    if (!card || !company) return;
    // The card's anchor is the tower's tip; it sits above it, centred.
    const ax = cr.left + (parseFloat(el.style.left) / 100) * cr.width;
    const ay = cr.top + (parseFloat(el.style.top) / 100) * cr.height;
    const w = card.offsetWidth;
    const bottom = ay - (el.offsetHeight - card.offsetHeight);
    const top = bottom - card.offsetHeight;
    const wanted = ax - w / 2;
    const left = Math.min(Math.max(wanted, pr.left + EDGE), pr.right - EDGE - w);
    const dx = left - wanted;
    const towerShown = ax > pr.left + EDGE && ax < pr.right - EDGE && top > pr.top + EDGE;
    // A nudge past half the card would leave the connector beside it.
    const connected = Math.abs(dx) <= w / 2 - 16;
    const clearOfText = text.every(
      (t) =>
        left + w + TEXT_GAP <= t.left ||
        left - TEXT_GAP >= t.right ||
        bottom + TEXT_GAP <= t.top ||
        top - TEXT_GAP >= t.bottom,
    );
    placement[company] = towerShown && connected && clearOfText ? Math.round(dx) : null;
  });
  return placement;
}

/**
 * The hero's city (city-model.ts), back on the home page since 2026-11-23,
 * redrawn for it: the team missed the old page's skyline, the one large
 * thing on its first screen, and the redesign's hero had words alone. It
 * is the old city's model in the new page's look: buildings in white and
 * cool grey with slate hairlines, the drafting grid's own line, on the
 * grid's ground plane; the towers that rise for a job that fits are in the
 * page's four feature colours, and each sends up the job as a white card.
 * No violet, no glow, no streaks of light and no fades, which the page
 * left behind (docs/marketing-design-system.md).
 *
 * Drawn only after hydration: rendered on the server it would add hundreds
 * of KB of path data to the page. It shows once its images have loaded, so
 * the towers never stand alone on bare ground, and then rises from behind
 * the hero's foot line, the back rows first (`--layer`, `.hero-city` in
 * landing.css). The job cards are HTML over it, placed in percent of the
 * strip so they track it as it scales, and shown only where they fit
 * (placeCards). Its panel is the nearest `[data-hero-panel]`.
 */
export function HeroCity() {
  // Null on the server and until the first effect, so the city still draws
  // only after hydration, and a phone never builds the wide one first.
  const phone = useMediaQuery(PHONE_QUERY);
  const rootRef = useRef<HTMLDivElement>(null);
  const [placement, setPlacement] = useState<Record<string, number | null>>({});
  const [loaded, setLoaded] = useState<ReadonlySet<string>>(() => new Set());

  // Built once the browser is idle, in a task of its own: built as the page
  // hydrated, it made one long task of both, 0.7 s at a 4x CPU slowdown
  // (KAN-540). The city comes in once its images load in any case.
  const [built, setBuilt] = useState<boolean | null>(null);
  useEffect(() => {
    if (phone === null) return;
    const build = () => {
      getLayers(phone);
      setBuilt(phone);
    };
    // Safari has no requestIdleCallback.
    if (typeof window.requestIdleCallback === "function") {
      const id = window.requestIdleCallback(build, { timeout: 800 });
      return () => window.cancelIdleCallback(id);
    }
    const timer = setTimeout(build, 1);
    return () => clearTimeout(timer);
  }, [phone]);
  const shown = phone !== null && built === phone;

  useEffect(() => {
    const root = rootRef.current;
    const panel = root?.closest<HTMLElement>("[data-hero-panel]");
    if (!shown || !root || !panel) return;
    const place = () => setPlacement(placeCards(root, panel));
    const observer = new ResizeObserver(place);
    observer.observe(panel);
    // The window too: the text can rewrap without the panel resizing.
    window.addEventListener("resize", place);
    // Again once the text has finished rising into place (its last piece
    // lands 1.2s after load).
    const settle = window.setTimeout(place, 1400);
    // Its loops stop while it is off screen (landing.css).
    const seen = new IntersectionObserver(([entry]) =>
      root.toggleAttribute("data-paused", !entry.isIntersecting),
    );
    seen.observe(root);
    return () => {
      seen.disconnect();
      observer.disconnect();
      window.removeEventListener("resize", place);
      window.clearTimeout(settle);
    };
  }, [shown]);

  if (!shown) return null;
  const city = getCity(phone);
  const layers = getLayers(phone);
  const ready = layers.every((layer) => !("still" in layer) || loaded.has(layer.still));
  const last = Math.max(1, layers.length - 1);

  return (
    <div ref={rootRef} className="hero-city" data-ready={ready ? "" : undefined} aria-hidden="true">
      <svg viewBox={VIEW_BOX} className="city-ground">
        <defs>
          {/* The ground runs out towards the text above it. */}
          <linearGradient
            id="hero-city-fade"
            x1="0"
            y1="120"
            x2="0"
            y2="300"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0" stopColor="#ffffff" stopOpacity="0" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="1" />
          </linearGradient>
          <mask
            id="hero-city-ground"
            maskUnits="userSpaceOnUse"
            x="0"
            y={STRIP_TOP}
            width={STRIP_WIDTH}
            height={STRIP_HEIGHT}
          >
            <rect
              y={STRIP_TOP}
              width={STRIP_WIDTH}
              height={STRIP_HEIGHT}
              fill="url(#hero-city-fade)"
            />
          </mask>
        </defs>
        <g mask="url(#hero-city-ground)">
          <path className="grid" d={city.grid} />
        </g>
      </svg>

      {layers.map((layer, i) =>
        "still" in layer ? (
          // eslint-disable-next-line @next/next/no-img-element -- a blob URL of an SVG made in the browser, which next/image cannot load
          <img
            key={layer.still}
            src={layer.still}
            alt=""
            draggable={false}
            className="city-layer"
            style={vars({ "--layer": i / last })}
            onLoad={() => setLoaded((had) => new Set(had).add(layer.still))}
          />
        ) : (
          <div
            key={layer.towers[0].index}
            className="city-layer"
            style={vars({ "--layer": i / last })}
          >
            {layer.towers.map(({ piece, index, hue }) => {
              const box = boundsOf(piece);
              const colour = TOWER_COLOURS[hue];
              const fill = `url(#city-tower-${index})`;
              return (
                <svg
                  // The model is fixed, so a piece's index is a stable key.
                  key={index}
                  viewBox={`${box.x} ${box.y} ${box.w} ${box.h}`}
                  className="city-tower"
                  style={vars({
                    left: `${(box.x / STRIP_WIDTH) * 100}%`,
                    top: `${((box.y - STRIP_TOP) / STRIP_HEIGHT) * 100}%`,
                    width: `${(box.w / STRIP_WIDTH) * 100}%`,
                    height: `${(box.h / STRIP_HEIGHT) * 100}%`,
                    "--turn": turnOf(piece.delay),
                  })}
                >
                  <defs>
                    <linearGradient
                      id={`city-tower-${index}`}
                      gradientUnits="userSpaceOnUse"
                      x1="0"
                      y1={box.y + box.h}
                      x2="0"
                      y2={box.y}
                    >
                      <stop offset="0" stopColor={colour.low} />
                      <stop offset="0.45" stopColor={colour.ground} />
                      <stop offset="1" stopColor={colour.high} />
                    </linearGradient>
                  </defs>
                  <path d={piece.gl} fill={fill} />
                  {/* The left face is the one in shade, as the buildings'. */}
                  <path d={piece.gl} fill={INK} opacity="0.1" />
                  <path d={piece.gr} fill={fill} />
                  <path d={piece.gt} fill={colour.roof} />
                  <path d={piece.wl} fill="none" stroke="#fff" strokeWidth="0.8" opacity="0.5" />
                  <path
                    d={piece.we}
                    fill="none"
                    stroke={colour.edge}
                    strokeWidth="1"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    opacity="0.7"
                  />
                </svg>
              );
            })}
          </div>
        ),
      )}

      {/* The job cards, on a layer of their own that rises with the front
          row. Hidden (but still measured) where a card does not fit. Until
          the first measurement, none shows. */}
      <div className="city-layer" style={vars({ "--layer": 1 })}>
        {city.tags.map((tag, i) => (
          <div
            key={tag.company}
            data-tag={tag.company}
            // With reduced motion the first card on each side shows, still.
            data-still={i < 2 ? "" : undefined}
            className={cn("city-tag", typeof placement[tag.company] !== "number" && "invisible")}
            style={vars({
              left: `${(tag.x / STRIP_WIDTH) * 100}%`,
              top: `${((tag.y - STRIP_TOP) / STRIP_HEIGHT) * 100}%`,
              "--turn": turnOf(tag.delay),
            })}
          >
            <div className="flex flex-col items-center">
              {/* The posting as the app shows one: its logo, role and
                company, then the match as its ring, its share and its band
                in words (never a bare number: lib/match.ts). White on the
                page, lifted by the float shadow. */}
              <div
                data-card
                style={{ transform: `translateX(${placement[tag.company] ?? 0}px)` }}
                className="text-ink flex items-center gap-2.5 rounded-xl bg-white py-2 pr-3 pl-2 whitespace-nowrap shadow-[var(--mk-shadow-float)]"
              >
                <FaviconLogo domain={tag.domain} eager className="size-8 rounded-lg" />
                <span className="flex flex-col text-left">
                  <span className="text-xs leading-4 font-medium">{tag.title}</span>
                  <span className="text-ink-meta text-[11px] leading-4">{tag.company}</span>
                </span>
                <span className="ml-1.5 flex flex-col items-end">
                  <span className="flex items-center gap-1 text-xs leading-4 font-semibold tabular-nums">
                    <MatchGlyph score={tag.score} className="size-3" />
                    {tag.score}%
                  </span>
                  <span className="text-ink-meta text-[11px] leading-4">
                    {matchTier(tag.score)}
                  </span>
                </span>
              </div>
              {/* The card's lead down to the tower's tip, ending on an ink
                square, the grid's own mark. */}
              <span className="bg-ink/35 h-5 w-px" />
              <span className="bg-ink size-[5px]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
