"use client";

import { DotsSixVerticalIcon } from "@phosphor-icons/react/ssr";
import {
  useCallback,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
} from "react";

import { PlusIcon } from "@/components/icons";
import { Tip } from "@/components/ui/tip";
import type { RenderBox } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

import {
  bandOn,
  blockAt,
  dropAt,
  siblingsOf,
  type BlockKind,
  type OutlineBlock,
  type Spot,
} from "./page-outline";

/**
 * The page's own handles (KAN-920): hover a section heading, an entry or a
 * bullet, and a + and a drag handle show in the margin beside it, as the
 * Sections panel's rows have, so a student moves and adds things where they
 * read them. The panel copied Jobright's side list, and teammates found the
 * editor too like it; the page is now the outline, and the panel optional.
 *
 * A drag is the pointer's own (not HTML drag and drop): the drop line is
 * drawn on the page, snapped to the dragged block's siblings only (a bullet
 * within its entry, an entry within its section, a section between
 * sections), and the drop goes to the editor, which shows the move at once.
 * A press on the handle with no drag picks the block (the breadcrumb's
 * level), and its arrow keys move it, as the panel's handles do.
 */

export type PageOutline = {
  /** The blocks of the page on screen, read from its boxes. */
  blocksOf: (boxes: RenderBox[]) => OutlineBlock[];
  /** The block picked from its handle or the breadcrumb, outlined. */
  picked: { kind: BlockKind; id: string } | null;
  onPick: (block: OutlineBlock) => void;
  /** Puts the block at `to` among its siblings once it is taken out. */
  onMove: (block: OutlineBlock, to: number) => void;
  /** Adds a sibling after the block, and what it adds ("School",
   *  "Bullet"); null where nothing can be added. */
  addOf: (block: OutlineBlock) => { noun: string; add: (opener: HTMLElement) => void } | null;
};

type Drag = {
  block: OutlineBlock;
  /** The pointer's start, to tell a press from a drag. */
  from: number;
  moved: boolean;
  drop: ReturnType<typeof dropAt> | null;
};

/** Pixels a press may wander before it is a drag. */
const DRAG_AFTER = 4;
/** Pixels from the window's top or foot where a drag scrolls the page. */
const EDGE = 56;

function scrollerOf(element: HTMLElement | null): HTMLElement | null {
  for (let at = element?.parentElement; at; at = at.parentElement) {
    const { overflowY } = getComputedStyle(at);
    if ((overflowY === "auto" || overflowY === "scroll") && at.scrollHeight > at.clientHeight)
      return at;
  }
  return document.scrollingElement as HTMLElement | null;
}

/** The hover, the drag and the pointer's place on the pages, shared by every
 *  page's layer, since a drag can cross a page break. */
export function usePageOutline({
  outline,
  blocks,
  pages,
  sizes,
}: {
  outline: PageOutline | undefined;
  blocks: OutlineBlock[];
  /** Each page's frame, in order. */
  pages: RefObject<(HTMLDivElement | null)[]>;
  sizes: { width: number; height: number }[];
}) {
  const [hover, setHover] = useState<string | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const dragging = useRef<Drag | null>(null);

  /** The pointer as a spot on the pages: the page under it, else the
   *  nearest one. */
  const spotOf = useCallback(
    (clientY: number): Spot | null => {
      let best: Spot | null = null;
      let distance = Infinity;
      pages.current?.forEach((frame, i) => {
        if (!frame || !sizes[i]) return;
        const rect = frame.getBoundingClientRect();
        const off = clientY < rect.top ? rect.top - clientY : Math.max(0, clientY - rect.bottom);
        if (off >= distance) return;
        distance = off;
        const y = ((clientY - rect.top) / rect.height) * sizes[i].height;
        best = { page: i + 1, y: Math.min(Math.max(y, 0), sizes[i].height) };
      });
      return best;
    },
    [pages, sizes],
  );

  const hoverAt = (clientY: number) => {
    if (!outline || dragging.current) return;
    const spot = spotOf(clientY);
    const size = spot && sizes[spot.page - 1];
    const block = spot && size ? blockAt(blocks, spot, size.height) : null;
    setHover(block ? `${block.kind}:${block.id}` : null);
  };

  const indexOf = (block: OutlineBlock) =>
    siblingsOf(blocks, block).findIndex((b) => b.id === block.id);

  const grip = (block: OutlineBlock) => ({
    onPointerDown: (event: PointerEvent<HTMLButtonElement>) => {
      if (event.button !== 0) return;
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      const next = { block, from: event.clientY, moved: false, drop: null };
      dragging.current = next;
      setDrag(next);
    },
    onPointerMove: (event: PointerEvent<HTMLButtonElement>) => {
      const now = dragging.current;
      if (!now) return;
      const moved = now.moved || Math.abs(event.clientY - now.from) > DRAG_AFTER;
      if (!moved) return;
      // Near the window's top or foot the page scrolls under the drag
      const edge = event.clientY < EDGE ? -12 : event.clientY > window.innerHeight - EDGE ? 12 : 0;
      if (edge) scrollerOf(event.currentTarget)?.scrollBy({ top: edge });
      const spot = spotOf(event.clientY);
      const next = { ...now, moved, drop: spot ? dropAt(blocks, now.block, spot) : now.drop };
      dragging.current = next;
      setDrag(next);
    },
    onPointerUp: () => {
      const now = dragging.current;
      dragging.current = null;
      setDrag(null);
      if (!now || !outline) return;
      if (!now.moved) return outline.onPick(block);
      if (now.drop && now.drop.to !== indexOf(block)) outline.onMove(block, now.drop.to);
    },
    onPointerCancel: () => {
      dragging.current = null;
      setDrag(null);
    },
    onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => {
      if (!outline) return;
      const by = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
      if (event.key === "Escape" && dragging.current) {
        dragging.current = null;
        setDrag(null);
        return;
      }
      if (!by) return;
      event.preventDefault();
      const to = indexOf(block) + by;
      if (to >= 0 && to < siblingsOf(blocks, block).length) outline.onMove(block, to);
    },
  });

  return {
    /** The block whose handle shows: the dragged one while a drag runs. */
    shown: drag ? `${drag.block.kind}:${drag.block.id}` : hover,
    drag,
    onPointerMove: (event: PointerEvent) => hoverAt(event.clientY),
    onPointerLeave: () => !dragging.current && setHover(null),
    grip,
  };
}

const pct = (value: number, of: number) => `${(value / of) * 100}%`;

/** One page's handles, drop line and outlines (`usePageOutline`). */
export function OutlineLayer({
  outline,
  blocks,
  page,
  size,
  state,
}: {
  outline: PageOutline;
  blocks: OutlineBlock[];
  page: number;
  size: { width: number; height: number };
  state: ReturnType<typeof usePageOutline>;
}) {
  const shown = blocks.find((b) => `${b.kind}:${b.id}` === state.shown);
  const picked = outline.picked
    ? blocks.find((b) => b.kind === outline.picked!.kind && b.id === outline.picked!.id)
    : undefined;
  const dragged = state.drag?.moved ? state.drag.block : undefined;
  const line = state.drag?.moved ? state.drag.drop?.line : undefined;
  const ring = (block: OutlineBlock, className: string) => {
    const band = bandOn(block, page, size.height);
    if (!band) return null;
    return (
      <div
        aria-hidden
        className={cn("pointer-events-none absolute rounded-xs", className)}
        style={{
          left: pct(block.x0 - 4, size.width),
          width: pct(block.x1 - block.x0 + 8, size.width),
          top: pct(band.top - 2, size.height),
          height: pct(band.bottom - band.top + 4, size.height),
        }}
      />
    );
  };
  const add = shown && !state.drag ? outline.addOf(shown) : null;
  return (
    <>
      {picked && ring(picked, "ring-brand ring-2")}
      {dragged && ring(dragged, "bg-brand/5 ring-brand/40 ring-1")}
      {line && line.page === page && (
        <div
          aria-hidden
          className="bg-brand pointer-events-none absolute z-20 h-0.5 -translate-y-1/2 rounded-full"
          style={{
            left: pct(line.x0 - 4, size.width),
            width: pct(line.x1 - line.x0 + 8, size.width),
            top: pct(line.y - 1, size.height),
          }}
        />
      )}
      {shown && shown.start.page === page && (
        <div
          data-keeps-selection
          className="absolute z-20 flex -translate-x-full -translate-y-1 items-center"
          style={{ left: pct(shown.x0 - 3, size.width), top: pct(shown.anchor, size.height) }}
        >
          {add && (
            <Tip label={`Add ${add.noun}`}>
              <button
                type="button"
                aria-label={`Add ${add.noun} after ${shown.label}`}
                onClick={(event) => add.add(event.currentTarget)}
                className="text-ink-meta hover:text-ink hover:bg-ink/5 focus-visible:ring-brand-ring flex size-5 items-center justify-center rounded-xs focus-visible:ring-2 focus-visible:outline-none"
              >
                <PlusIcon className="size-3.5" />
              </button>
            </Tip>
          )}
          <button
            type="button"
            aria-label={`Move ${shown.label}`}
            {...state.grip(shown)}
            className="text-ink-meta hover:text-ink hover:bg-ink/5 focus-visible:ring-brand-ring flex h-5 w-4 cursor-grab touch-none items-center justify-center rounded-xs focus-visible:ring-2 focus-visible:outline-none active:cursor-grabbing"
          >
            <DotsSixVerticalIcon aria-hidden weight="bold" className="size-4" />
          </button>
        </div>
      )}
    </>
  );
}
