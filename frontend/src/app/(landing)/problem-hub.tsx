"use client";

import {
  BrowsersIcon,
  ChatSlashIcon,
  FilesIcon,
  PencilSimpleLineIcon,
  RepeatIcon,
  TableIcon,
} from "@phosphor-icons/react/ssr";
import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type FocusEvent,
  type PointerEvent,
  type ReactNode,
} from "react";

import { cn } from "@/lib/cn";

import { useArrived, useLoopsHeld } from "./hooks";

type Scene = "boards" | "resumes" | "forms" | "question" | "tracker" | "replies";
type Problem = { scene: Scene; title: string; body: string };

/** Each problem's glyph: the thing it is about (the user's picks,
 *  2026-11-20). The first is two browser windows, many sites open at once
 *  (the user's pick of nine, 2026-11-21): it was a folded map, which read
 *  as tidy where the card is about a mess. The third is the repeat
 *  arrows (the user's pick of seven the same day; it was two stacked
 *  squares, the copy glyph). The fourth is a pencil on a line (the
 *  user's pick of seven; it was an hourglass). The sixth is a message
 *  struck through (the user's pick of seven; it was Phosphor's envelope
 *  with its cross set on the corner, two glyphs put together by hand,
 *  since the library has no rejected letter). All six are single Phosphor
 *  glyphs now. */
const ICONS = {
  boards: BrowsersIcon,
  resumes: FilesIcon,
  forms: RepeatIcon,
  question: PencilSimpleLineIcon,
  tracker: TableIcon,
  replies: ChatSlashIcon,
};

/** How long each card stays open before the next one opens, in ms. The
 *  browser picture's four tabs make one pass in the same time, so the hub
 *  has one clock (`--board-loop`, landing.css). */
const TURN = 8000;

/** The three-column layout, where the cards take turns. */
const WIDE = "(min-width: 64rem)";
const watchWide = (onChange: () => void) => {
  const query = window.matchMedia(WIDE);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
};

/**
 * The problems hub (problems.tsx, KAN-923, the user's layout): the six
 * problems of a search, three before applying on the left and three after
 * on the right, and one large visual in the middle showing the open one.
 * A click, a tap or Enter opens a problem, never a hover (the user's call:
 * opened on hover, the cards changed under a passing pointer). Every
 * problem's words stay on screen, so only the picture changes.
 *
 * **The cards take turns** (the user's idea, 2026-11-21, so a reader
 * learns the cards switch the picture: nothing said they could be
 * clicked). A hairline draws clockwise round the open card over `TURN`
 * (`.card-ring` in landing.css), and when it closes the next card opens,
 * in the order of a search, round again after the sixth. It follows the
 * product rows' rules (product-accordion.tsx): it plays only while the
 * hub is well on screen, the tab is shown and no pointer or keyboard
 * focus is on a card (a reader there is reading); with reduced motion
 * nothing turns and there is no ring.
 *
 * **A click opens a card and the turns go on from it**, its ring drawn
 * again from empty (the user's catch, 2026-11-21: "when I clicked a card,
 * the progress doesn't appear anymore"). The first version stopped the
 * turns for good on a click, as the product rows do, and took the ring
 * away; the reader saw the timer vanish and read it as broken. So the
 * way to hold a card is to keep the pointer or the keyboard's focus on
 * it, and the ring shows that it is held: **a faint track runs round the
 * open card all the time**, so the timer never disappears, and the dark
 * line stands still on it. Without the track, a card just clicked showed
 * no ring at all, since its line was empty and held under the pointer.
 * A mouse click's own focus does not hold the turn, only focus a
 * keyboard put there (`:focus-visible`): a clicked button keeps focus
 * after the pointer leaves, and the turn never started again.
 *
 * Three limits beyond those. **One clock**: the browser picture's tabs
 * make one pass per turn and are held whenever the ring is (`data-held`),
 * so the hub never runs two timers at two speeds; below lg, where nothing
 * turns, the tabs keep their own slower loop.
 * **From lg up only**: below it the picture sits above the list, so a
 * card that opened by itself would move the lit row under the reader's
 * thumb. **The ring is quiet**: 1.5px in ink at half strength, at one
 * steady speed, so it reads as a timer and not as a second focus.
 * This replaced "nothing changes on a timer", which the hub's first
 * version held to; the taste rules ban timed tabs, and WorkIt's own
 * design system allows a turn the reader can hold.
 *
 * Each visual plays once as it shows: the stage carries `data-arrived` as
 * `Arrive` does, "false" until it is well on screen and again for two
 * frames after a switch, so the new visual mounts in its waiting pose and
 * then plays (the `.journey-*` classes); it also mounts afresh once
 * hydrated (its key reads `mounted`). No attribute in the server's HTML, so
 * the first visual shows finished without script.
 *
 * Below lg the stage leads, then the problems: in two columns from md, one
 * on a phone. From lg up the hub is one block: each side's three cards
 * fill the stage's height. From xl up the stage stands 1.5rem above and
 * below the card stacks (the columns' `xl:py-6`, the user's ask,
 * 2026-11-21): level with them, it read as a seventh card. From md up
 * the six cards are one height (`md:auto-rows-fr`, the user's ask,
 * 2026-11-21: rows as tall as their words read as inconsistent), so the
 * longest card sets every card's height; a card is written to one line of
 * title and about 60 characters under it. On a phone each card keeps its
 * own height. Set loosely in the middle of each column, the cards were
 * shorter than the stage and the section read as small and tall at once
 * (the user's catch). **The visual is the hub's main piece** (the user's
 * asks, 2026-11-21 and 2026-11-23): the hub is wider than the page's
 * column (83rem, problems.tsx) and the side columns are 19.75rem each
 * from xl (narrower, a card's longest title took two lines and every card
 * grew), so the stage is about twice a side column, 608px at 1440 (it was
 * 432px, with 20rem pictures the user found squished), and a picture is
 * up to 30rem wide, drawn 1.1 or 1.15 times its size where the stage has
 * the room (`.problem-window` in landing.css: by the screen's size, since
 * on a short screen a larger visual was cut at the stage's foot). The band fits the screen with about 4rem to spare:
 * the stage is `clamp(23rem, 100svh - 23.5rem, 30rem)` tall and grows to
 * the cards' height, what is left once the band's padding, the heading
 * and its one-line subtitle are counted (measured at 1440 × 800: the band
 * 738px, the stage 432 × 424). At 794px on an 800px screen the reader had
 * to scroll it into place exactly (the user's catch, 2026-11-21). Change
 * this height and the visual's sizes in landing.css together.
 *
 * **Colour (the user's pick of three previews, 2026-11-21).** It stands on
 * the band's light grey (problems.tsx). The five closed cards have no box:
 * their words sit on the band, each glyph on a white tile, with a faint
 * white fill under the pointer. The open card is the one white, lifted
 * card, its glyph on an ink tile. The stage is a well a step darker than
 * the band (`.problem-well` in landing.css), so the picture's white window
 * stands out on it, and the open card and the window are one material,
 * white on grey: the pair says which card shows which picture.
 *
 * Why. The open card was solid ink with white words. That made a card at
 * the side the strongest shape in the section, while the picture, the
 * point of it, sat on the weakest ground (a white window on a stage of
 * white at 60%). And six white cards and the stage were seven boxes of
 * about one weight, so nothing led. Contrast is a budget: it goes where
 * the eye should. Before the ink the open card was a pale violet tint,
 * which read as off theme, and a violet edge, which read as a button (the
 * user's catches, 2026-11-20); the band itself was near-black for a day.
 *
 * The section's one figure (81%, with its source) stood under the hub as
 * an outlined strip until 2026-11-21, when the user archived it: at the
 * hub's foot it read as hiding. It is `ProblemStat` (problem-stat.tsx),
 * unmounted, until it has a better place.
 *
 * The problems are buttons with `aria-pressed`, not tabs: the visuals are
 * pictures (`aria-hidden`), and each button's words are its name.
 */
export function ProblemHub({
  problems,
  scenes,
}: {
  problems: readonly Problem[];
  scenes: readonly ReactNode[];
}) {
  const [at, setAt] = useState(0);
  const [hold, setHold] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(stageRef, mounted);

  // Counts the reader's own picks, so a click starts that card's turn (its
  // ring and its picture) again from the start, even on the open card.
  const [picks, setPicks] = useState(0);
  const [inView, setInView] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [focused, setFocused] = useState(false);
  const hidden = useLoopsHeld();
  const rootRef = useRef<HTMLDivElement>(null);
  const wide = useSyncExternalStore(
    watchWide,
    () => window.matchMedia(WIDE).matches,
    () => false,
  );

  // The turns run only while the hub is well on screen.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {
      threshold: 0.35,
    });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  const turning = wide;
  const resting = hovering || focused;
  const playing = turning && inView && arrived && !hold && !hidden && !resting;
  const turnKey = `${at}:${picks}`;

  const openCard = (i: number) => {
    setHold(true);
    setAt(i);
    // Two frames: the new visual paints once in its waiting pose, then plays.
    requestAnimationFrame(() => requestAnimationFrame(() => setHold(false)));
  };
  const pick = (i: number) => {
    setPicks((count) => count + 1);
    openCard(i);
  };

  // A pointer or the keyboard's focus on the cards holds the turn: a reader
  // there is reading. A mouse only, since a touch leaves no pointer behind;
  // and focus the keyboard put there only, since a clicked button keeps
  // focus after the pointer has gone.
  const rest = {
    onPointerEnter: (event: PointerEvent) => event.pointerType === "mouse" && setHovering(true),
    onPointerLeave: (event: PointerEvent) => event.pointerType === "mouse" && setHovering(false),
    onFocus: (event: FocusEvent) => setFocused(event.target.matches(":focus-visible")),
    onBlur: (event: FocusEvent) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
    },
  };

  const half = Math.ceil(problems.length / 2);
  const column = (from: number, to: number, className: string) => (
    <div className={cn("grid gap-2.5 md:auto-rows-fr", className)} {...rest}>
      {problems.slice(from, to).map((problem, j) => {
        const i = from + j;
        const open = i === at;
        const Icon = ICONS[problem.scene];
        return (
          <button
            key={problem.title}
            type="button"
            aria-pressed={open}
            onClick={() => pick(i)}
            className={cn(
              "relative flex items-start gap-3.5 rounded-2xl px-4 py-3.5 text-left transition-[background-color,box-shadow] duration-200 md:items-center",
              "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
              // The open card is the one white, lifted card; the rest are words
              // on the band, with a faint fill under the pointer.
              open ? "bg-white shadow-(--mk-shadow-float)" : "hover:bg-white/60",
            )}
          >
            <span
              className={cn(
                "grid size-9 shrink-0 place-items-center rounded-[10px] transition-colors duration-200",
                open ? "bg-ink text-white" : "text-ink-meta bg-white",
              )}
            >
              <Icon aria-hidden="true" className="size-[18px]" />
            </span>
            <span className="min-w-0">
              <span className="text-ink block text-[15px] leading-snug font-medium">
                {problem.title}
              </span>
              <span className="text-ink-meta mt-1 block text-[13.5px] leading-snug text-pretty">
                {problem.body}
              </span>
            </span>
            {/* The open card's turn: a faint track round its edge, always
                there, and a hairline drawn along it, which opens the next
                card when it closes. Keyed by the turn, so each one draws
                from empty. Inset by half its width, so the line's outer
                edge is the card's. Gone with reduced motion, where nothing
                turns. */}
            {open && turning && (
              <svg
                key={turnKey}
                aria-hidden="true"
                className="pointer-events-none absolute inset-[0.75px] size-[calc(100%-1.5px)] overflow-visible motion-reduce:hidden"
              >
                <rect width="100%" height="100%" rx="15.25" className="card-track" />
                <rect
                  width="100%"
                  height="100%"
                  rx="15.25"
                  pathLength="1"
                  className="card-ring"
                  style={{
                    animationDuration: `${TURN}ms`,
                    animationPlayState: playing ? "running" : "paused",
                  }}
                  onAnimationEnd={() => openCard((at + 1) % problems.length)}
                />
              </svg>
            )}
          </button>
        );
      })}
    </div>
  );

  return (
    <div ref={rootRef} className="mt-8">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-[17rem_minmax(0,1fr)_17rem] lg:gap-3 xl:grid-cols-[19.75rem_minmax(0,1fr)_19.75rem]">
        {column(0, half, "lg:order-1 xl:py-6")}
        <div
          ref={stageRef}
          data-arrived={mounted ? String(arrived && !hold) : undefined}
          // Where the cards turn, the browser picture's tabs keep the cards'
          // clock: one pass a turn, and held whenever the ring is.
          data-held={(turning && !playing) || undefined}
          style={turning ? ({ "--board-loop": `${TURN}ms` } as CSSProperties) : undefined}
          className="problem-well relative order-first h-[22rem] overflow-hidden rounded-2xl md:col-span-2 md:h-[27rem] lg:order-2 lg:col-span-1 lg:h-auto lg:min-h-[clamp(23rem,calc(100svh-23.5rem),30rem)]"
        >
          {/* A dot grid on the stage, fading toward the middle where the
              visual sits (`.problem-dots`, the user's pick of six patterns,
              2026-11-20): a flat stage read as boring. */}
          <div aria-hidden="true" className="problem-dots absolute inset-0" />
          {/* Keyed by `mounted` too: the visual mounts afresh once hydrated,
              so a transition the server's HTML would skip plays when seen. */}
          <div key={mounted ? turnKey : "server"} className="absolute inset-0">
            {scenes[at]}
          </div>
        </div>
        {column(half, problems.length, "lg:order-3 xl:py-6")}
      </div>
    </div>
  );
}

const noSubscribe = () => () => {};
