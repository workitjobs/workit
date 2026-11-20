import type { CSSProperties } from "react";

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
 * Plain markup with no hooks, so a server or a client component can draw
 * it. Decoration, hidden from assistive technology.
 */
export function DraftLines({ gap = "1.25rem" }: { gap?: string }) {
  return (
    <span aria-hidden="true" className="draft" style={{ "--gap": gap } as CSSProperties}>
      <span className="draft-h top-0" />
      <span className="draft-h bottom-0" />
      <span className="draft-v left-0" />
      <span className="draft-v right-0" />
      <i className="top-0 left-0" />
      <i className="top-0 left-full" />
      <i className="top-full left-0" />
      <i className="top-full left-full" />
    </span>
  );
}
