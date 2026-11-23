"use client";

import { useRef, useSyncExternalStore, type CSSProperties } from "react";

import { useArrived } from "./hooks";

/**
 * The drafting grid's frame (KAN-923, after Loopsii's, the user's call to
 * frame every section, 2026-11-20): two hairlines across the window at a
 * block's top and foot, two down its sides that run on past it, and a
 * small ink square where they cross, as a drawing's registration marks.
 * It sits `gap` above and below the block and 1.5rem outside the
 * container's content on each side, the same for every section, so the
 * side lines form one rail down the page; it takes no room and changes no
 * layout, and draws over nothing: its parent is `relative`, spans the
 * container's width, and keeps clear of the lines. From lg up (`.draft`
 * in landing.css): below it the lines ran along the window's edge.
 *
 * **It draws itself as it arrives** (2026-11-21, the user's ask for
 * transitions between the sections, in the hero's own vocabulary): the top
 * line grows from the centre, the side lines draw down, the foot line
 * grows, and an ink square pops at each corner as its lines reach it
 * (`.draft[data-arrived]` in landing.css). In time, once the frame is well
 * on screen, never scrubbed by the scroll (`useArrived`), and again only
 * after the reader has scrolled back above it. No `data-arrived` in the
 * server's HTML, so without script, and with reduced motion, the frame is
 * simply there. The page's first frame takes no part: the page's own
 * entrance draws it (the `load-*` rules).
 *
 * A client component for that one observer; a server or a client component
 * can draw it. Decoration, hidden from assistive technology.
 */
export function DraftLines({
  gap = "1.25rem",
  first,
}: {
  gap?: string;
  /** The page's first frame (the home hero's), which hangs from the
   *  header: its top edge is the header's foot, and the header draws that
   *  line, its ink squares and the rails above it (`.header-line`,
   *  `.header-marks`), so this frame draws no top line, takes no gap
   *  above, and starts its side lines at its top; they end at its foot
   *  line, on its two squares. **The hero's city is drawn over these
   *  lines** (page.tsx): they show in the open sky beside the headline
   *  and pass behind the buildings. Drawn over the city (until
   *  2026-11-23) they crossed its buildings, and with no side lines at
   *  all (for a few hours) the squares marked no crossing and the first
   *  screen showed none of the page's grid. */
  first?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  // False on the server and while hydrating, true after (as `Arrive`).
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const watching = mounted && !first;
  const arrived = useArrived(ref, watching);
  return (
    <span
      ref={ref}
      aria-hidden="true"
      className={first ? "draft draft-first" : "draft"}
      data-arrived={watching ? String(arrived) : undefined}
      style={{ "--gap": gap } as CSSProperties}
    >
      {!first && <span className="draft-h top-0" />}
      <span className="draft-h bottom-0" />
      <span className="draft-v left-0" />
      <span className="draft-v right-0" />
      {!first && (
        <>
          <i className="top-0 left-0" />
          <i className="top-0 left-full" />
        </>
      )}
      <i className="top-full left-0" />
      <i className="top-full left-full" />
    </span>
  );
}

const noSubscribe = () => () => {};
