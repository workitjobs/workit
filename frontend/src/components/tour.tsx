"use client";

import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { HandPointingIcon } from "@phosphor-icons/react/ssr";
import { createPortal } from "react-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/** What a coach mark points at: `data-tour` names (several lit as one), or
 *  a selector for a control that carries none (a line on the resume). */
export type CoachTarget = { tour?: string | string[]; selector?: string; fallback?: string };

/** One of a coach mark's buttons; the last primary one is the way on. */
export type CoachAction = {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
};

/** Wide enough for a walkthrough: from 64rem. A phone's editor is another
 *  layout, and none is drawn there (2026-11-17, the user's call). */
const WIDE = "(min-width: 64rem)";
const subscribe = (change: () => void) => {
  const query = window.matchMedia(WIDE);
  query.addEventListener("change", change);
  return () => query.removeEventListener("change", change);
};
export const useTourFits = () =>
  useSyncExternalStore(
    subscribe,
    () => window.matchMedia(WIDE).matches,
    () => false,
  );

const GAP = 12;
const EDGE = 16;
const CARD_WIDTH = 320;
/** The lit box's room around its control. */
const PAD = 6;

type Box = { top: number; left: number; width: number; height: number };

function find(target: CoachTarget): HTMLElement[] {
  const named = (names: string[]) =>
    names.flatMap((name) => [
      ...document.querySelectorAll<HTMLElement>(`[data-tour="${CSS.escape(name)}"]`),
    ]);
  const shown = (els: HTMLElement[]) => els.filter((el) => el.offsetWidth > 0);
  let found = shown(named(target.tour ? [target.tour].flat() : []));
  if (!found.length && target.selector) {
    const first = document.querySelector<HTMLElement>(target.selector);
    found = first ? shown([first]) : [];
  }
  if (!found.length && target.fallback) found = shown(named([target.fallback]));
  return found;
}

/** Where the target is now, as one box, or null when none is on screen;
 *  and whether a dialog covers the page (a form a step opened), when the
 *  coach mark steps aside. Read every frame while it shows, since panels
 *  slide and the page scrolls under it; state is set only on a change. */
function useTarget(target: CoachTarget | null, key: string, beacon?: string) {
  const [box, setBox] = useState<Box | null>(null);
  const [ring, setRing] = useState<Box | null>(null);
  const [covered, setCovered] = useState(false);
  const held = useRef(target);
  const heldBeacon = useRef(beacon);
  useEffect(() => {
    held.current = target;
    heldBeacon.current = beacon;
  });
  useEffect(() => {
    if (!held.current) return;
    let frame = 0;
    let last = "";
    const read = () => {
      const rects = held.current ? find(held.current).map((el) => el.getBoundingClientRect()) : [];
      const next: Box | null = rects.length
        ? (() => {
            const top = Math.min(...rects.map((r) => r.top));
            const left = Math.min(...rects.map((r) => r.left));
            return {
              top,
              left,
              width: Math.max(...rects.map((r) => r.right)) - left,
              height: Math.max(...rects.map((r) => r.bottom)) - top,
            };
          })()
        : null;
      const dialog = Boolean(document.querySelector('[data-slot="dialog-content"]'));
      const mark = heldBeacon.current
        ? document.querySelector<HTMLElement>(heldBeacon.current)
        : null;
      const r = mark && mark.offsetWidth > 0 ? mark.getBoundingClientRect() : null;
      const ringBox = r && { top: r.top, left: r.left, width: r.width, height: r.height };
      const round = (b: Box | null) => (b ? Object.values(b).map(Math.round).join(",") : "none");
      const now = `${round(next)}|${round(ringBox)}|${dialog}`;
      if (now !== last) {
        last = now;
        setBox(next);
        setRing(ringBox);
        setCovered(dialog);
      }
      frame = requestAnimationFrame(read);
    };
    read();
    return () => cancelAnimationFrame(frame);
  }, [key]);
  return { box: target ? box : null, ring: beacon ? ring : null, covered };
}

/**
 * A coach mark over a working screen (2026-11-17, the resume editor's
 * walkthrough, ../app/(seeker)/resumes/[resumeId]/walkthrough.tsx): it dims
 * the screen but for one control, lit in brand, and a card beside it says
 * what the control is for and what to try. The screen decides the step, its
 * words and its buttons, and moves on when the student has done the thing:
 * a coach mark only points (2026-11-18: a tour that ran its own fixed order
 * of one action per section assumed one school, one job and one project).
 *
 * The dim is the lit box's own shadow, and nothing else covers the page, so
 * every control still works under it: it points, it never blocks. It steps
 * aside while a dialog is open (a form a step opened) and comes back when it
 * closes. The card is a non-modal dialog that announces each step, with
 * End Tour at its left. Not drawn below 64rem (`useTourFits`).
 */
export function CoachMark({
  id,
  target,
  eyebrow,
  title,
  children,
  art,
  beacon,
  actions,
  onEnd,
}: {
  /** A new id is a new step: the card is read out again. */
  id: string;
  target: CoachTarget | null;
  /** Where the student is ("Step 3 of 9"), a badge over the title. */
  eyebrow?: string;
  title: string;
  children: ReactNode;
  /** A small picture under the words (a tool that is not on screen yet). */
  art?: ReactNode;
  /** The control to press, as a selector: a ring pulses round it, so the
   *  card need not say "press +" (2026-11-18, the user's call: show, do not
   *  tell). */
  beacon?: string;
  actions: CoachAction[];
  onEnd: () => void;
}) {
  const fits = useTourFits();
  const { box, ring, covered } = useTarget(fits ? target : null, `${id}`, beacon);

  // THE SCREEN HOLDS STILL WHILE A STEP SHOWS (2026-11-18, the user's call):
  // the wheel and a touch drag scroll nothing, on the page or in a panel.
  // Scrolled, the lit box and its card rode up with the panel. Each step
  // brings its own control into view instead (below), so nothing it points
  // at is out of reach. A dialog a step opened (the entry form) scrolls as
  // ever: the coach mark steps aside while it is open.
  const holding = fits && !covered;
  useEffect(() => {
    if (!holding) return;
    const hold = (event: Event) => event.preventDefault();
    window.addEventListener("wheel", hold, { passive: false });
    window.addEventListener("touchmove", hold, { passive: false });
    return () => {
      window.removeEventListener("wheel", hold);
      window.removeEventListener("touchmove", hold);
    };
  }, [holding]);
  // As a step opens, its control (the ring's, else the lit one) scrolls into
  // view, but only when it is not on screen already: Format's Reset
  // Formatting sits at the foot of a long panel, and a line on the page can
  // sit below the fold. The scroll is smooth, and the lit box and card fade
  // out while it runs and back in where it lands (`moving`): scrolled at
  // once, every step snapped the page, and the box glided from where the
  // last control had been while this one moved under it (2026-11-18). A
  // beat later than the step, so the panel it opened has drawn.
  const aim = useRef({ target, beacon });
  useEffect(() => {
    aim.current = { target, beacon };
  });
  const [moving, setMoving] = useState(false);
  useEffect(() => {
    if (!fits) return;
    let settle = 0;
    // Checked at once, so a step that must scroll fades out before its box
    // starts toward the old place; again a beat later when its control has
    // not drawn yet (a panel the step just opened)
    const run = () => {
      const { target: t, beacon: b } = aim.current;
      const el = (b && document.querySelector<HTMLElement>(b)) || (t ? find(t)[0] : null);
      if (!el) return false;
      const r = el.getBoundingClientRect();
      // On screen already: a short control whole, clear of the edges; one
      // taller than half the window (the Header's fields, a whole panel) once
      // its top shows in the window's upper third. Judged whole, a panel a
      // few pixels taller than the window faded out for a scroll that went
      // nowhere (2026-11-18)
      const tall = r.height > window.innerHeight / 2;
      const shown = tall
        ? r.top >= 0 && r.top <= window.innerHeight / 3
        : r.top >= EDGE && r.bottom <= window.innerHeight - EDGE;
      if (shown) return true;
      // A short control to the middle, clear of the edge the lit box's
      // padding needs; a tall one to the top, so its first field shows
      const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      setMoving(!still);
      el.scrollIntoView({
        block: tall ? "start" : "center",
        inline: "nearest",
        behavior: still ? "auto" : "smooth",
      });
      settle = window.setTimeout(() => setMoving(false), 500);
      return true;
    };
    let later = 0;
    const first = requestAnimationFrame(() => {
      if (!run()) later = window.setTimeout(run, 150);
    });
    return () => {
      cancelAnimationFrame(first);
      window.clearTimeout(later);
      window.clearTimeout(settle);
    };
  }, [id, fits]);
  const card = useRef<HTMLDivElement>(null);
  const [cardHeight, setCardHeight] = useState(200);
  useLayoutEffect(() => {
    if (card.current) setCardHeight(card.current.offsetHeight);
  }, [id, box]);
  const titleId = useId();
  // THE LIT BOX GLIDES ONLY FROM ONE STEP TO THE NEXT (2026-11-18): for a
  // moment after the step changes. A scroll moves it every frame, and with
  // the glide always on it trailed the control by 300ms and slid about while
  // the student scrolled the panel; now it sticks to the control.
  const [glideFor, setGlideFor] = useState<string | null>(null);
  const [stepWas, setStepWas] = useState(id);
  if (stepWas !== id) {
    setStepWas(id);
    setGlideFor(id);
  }
  useEffect(() => {
    if (glideFor === null) return;
    const done = window.setTimeout(() => setGlideFor(null), 350);
    return () => window.clearTimeout(done);
  }, [glideFor]);

  if (!fits || covered) return null;

  // The card beside the lit box: on its left when there is room (the panel
  // sits at the window's right), else its right, else under it; its top
  // level with the box's, kept on screen. With nothing to light, it sits at
  // the foot of the window, centred.
  let place: { top: number; left: number } | null = null;
  if (box) {
    const fitsLeft = box.left - PAD - GAP - CARD_WIDTH >= EDGE;
    const fitsRight = box.left + box.width + PAD + GAP + CARD_WIDTH <= window.innerWidth - EDGE;
    const top = Math.min(Math.max(box.top, EDGE), window.innerHeight - cardHeight - EDGE);
    place = fitsLeft
      ? { top, left: box.left - PAD - GAP - CARD_WIDTH }
      : fitsRight
        ? { top, left: box.left + box.width + PAD + GAP }
        : {
            top: Math.min(box.top + box.height + PAD + GAP, window.innerHeight - cardHeight - EDGE),
            left: Math.min(Math.max(box.left, EDGE), window.innerWidth - CARD_WIDTH - EDGE),
          };
  }

  return createPortal(
    <>
      {box && (
        <div
          aria-hidden
          className={cn(
            "ring-brand rounded-control pointer-events-none fixed z-40 shadow-[0_0_0_9999px_rgb(18_26_40/0.32)] ring-2 transition-opacity duration-150",
            glideFor === id &&
              "transition-[top,left,width,height,opacity] duration-300 ease-out motion-reduce:transition-none",
            moving && "opacity-0",
          )}
          style={{
            top: box.top - PAD,
            left: box.left - PAD,
            width: box.width + PAD * 2,
            height: box.height + PAD * 2,
          }}
        />
      )}
      {ring && (
        // THE CONTROL TO PRESS: a pointing hand taps it, and a ring spreads
        // from the fingertip at the tap (`animate-coach-*`, globals.css). A
        // ping twice the control's size came first and read as far too big
        // (2026-11-18)
        <span
          aria-hidden
          className={cn("pointer-events-none fixed z-50", moving && "opacity-0")}
          style={{ top: ring.top, left: ring.left, width: ring.width, height: ring.height }}
        >
          <span className="ring-brand motion-safe:animate-coach-wave absolute inset-0 rounded-full opacity-0 ring-2 motion-reduce:hidden" />
          {/* The fingertip (11px in, 2px down in the 24px glyph) on the
              control's middle; white under an ink outline, as a pointer */}
          <span className="motion-safe:animate-coach-hand absolute top-[calc(50%-2px)] left-[calc(50%-11px)] size-6 origin-[11px_2px] drop-shadow-sm">
            <HandPointingIcon weight="fill" className="absolute inset-0 size-6 text-white" />
            <HandPointingIcon className="text-ink absolute inset-0 size-6" />
          </span>
        </span>
      )}
      {/* ONE CARD FOR THE WHOLE WALK: it glides with the lit box from step to
          step and its words fade in, where a card per step snapped to each
          new place (2026-11-18) */}
      <div
        ref={card}
        role="dialog"
        aria-modal="false"
        aria-labelledby={titleId}
        aria-live="polite"
        style={
          place ? { top: place.top, left: place.left, width: CARD_WIDTH } : { width: CARD_WIDTH }
        }
        className={cn(
          "bg-panel border-border-surface rounded-card shadow-lift fixed z-50 border p-4 transition-opacity duration-150",
          glideFor === id &&
            "transition-[top,left,opacity] duration-300 ease-out motion-reduce:transition-none",
          !place && "bottom-6 left-1/2 -translate-x-1/2",
          moving && "opacity-0",
        )}
      >
        <div key={id} className="motion-safe:animate-fade flex flex-col gap-2">
          {/* Where the student is, as a status badge (2026-11-18): a grey line
            of text read as a stray caption over the title */}
          {eyebrow && (
            <span className="flex">
              <Badge variant="status" tone="brand">
                {eyebrow}
              </Badge>
            </span>
          )}
          <h2 id={titleId} className="text-subtitle text-ink">
            {title}
          </h2>
          <div className="text-body text-ink-muted flex flex-col gap-2">{children}</div>
          {art}
          <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
            <Button variant="ghost" size="sm" className="mr-auto -ml-2" onClick={onEnd}>
              End Tour
            </Button>
            {actions.map((action) => (
              <Button
                key={action.label}
                size="sm"
                variant={action.variant === "secondary" ? "secondary" : "default"}
                onClick={action.onClick}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
