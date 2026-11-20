"use client";

import { ArrowUpRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Fit } from "./fit";
import { useLoopsHeld } from "./hooks";
import { StudioBox, TYPE } from "./layout-parts";

export type ProductItem = {
  title: string;
  body: string;
  /** The row's mark, rendered by the server (a feature page section's icon). */
  icon: ReactNode;
  /** Its deep dive on the feature page (`deepDiveAnchor`). */
  href: string;
  visual: ReactNode;
};

/** How long each row stays open before the next opens, in ms. */
const TURN = 6000;

/**
 * A product section's heading, rows and picture (product-sections.tsx,
 * KAN-923), after Calendly's product sections: the rows open one after
 * another on their own, as Calendly's do (the user's ask, 2026-11-20). The
 * open row shows its body and its arrow link to its deep dive, a line in
 * the feature's colour fills along its foot over `TURN` (`.row-fill` in
 * landing.css), and when it is full the next row opens, back to the first
 * after the last; the box shows the open row's still scene, swapping with a
 * fade.
 *
 * It plays only while someone can watch: with the section well on screen,
 * the tab shown, and no pointer or keyboard focus on the rows (a reader
 * there is reading). A click or tap on a row opens it and stops the turns
 * for good, its line full: the reader has taken over, and it is the way to
 * stop the motion that WCAG 2.2.2 asks for. With reduced motion nothing
 * turns, each line is full, and a click opens a row.
 *
 * It replaced a pinned version where the scroll opened the rows (each row
 * a stretch of scroll, the section held still at the screen's middle):
 * each product took two to three screens, and four of them most of the
 * page (the web review). Below lg the box sits between the heading and the
 * rows (one tree, `display: contents`).
 */
export function ProductAccordion({
  heading,
  items,
  ground,
  accent,
  flip,
}: {
  /** The feature's chip and heading, rendered by the server. */
  heading: ReactNode;
  items: ProductItem[];
  /** The box's ground: the feature's `studioGround`. */
  ground: string;
  /** The feature's colour: the open row's line. */
  accent: string;
  /** Box on the left from lg up, so the sections alternate sides. */
  flip?: boolean;
}) {
  const [active, setActive] = useState(0);
  // Once the reader picks a row, the turns stop and stay stopped.
  const [taken, setTaken] = useState(false);
  const [inView, setInView] = useState(false);
  const [resting, setResting] = useState(false);
  const hidden = useLoopsHeld();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLOListElement>(null);
  const id = useId();
  // The rows' height with the longest body open, so the column keeps one
  // height whichever row is open: grown and shrunk with each row, the
  // section shifted by up to 10px.
  const [listHeight, setListHeight] = useState<number>();

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const measure = () => {
      let titles = 0;
      let body = 0;
      list.querySelectorAll<HTMLElement>(":scope > li").forEach((row) => {
        titles += row.querySelector("h3")?.offsetHeight ?? 0;
        body = Math.max(body, row.querySelector<HTMLElement>("[data-body]")?.offsetHeight ?? 0);
      });
      // One hairline under each row and one over the first.
      setListHeight(titles + body + list.children.length + 1);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    return () => observer.disconnect();
  }, [items.length]);

  // The turns run only while the section is well on screen.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {
      threshold: 0.35,
    });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  const playing = !taken && inView && !hidden && !resting;

  const pick = (i: number) => {
    setTaken(true);
    setActive(i);
  };

  return (
    <div
      ref={rootRef}
      className="grid w-full gap-y-8 lg:grid-cols-2 lg:items-center lg:gap-x-16 lg:gap-y-0"
    >
      {/* The heading at the top of the column and the rows at its foot,
          level with the box; below lg its children join the grid so the
          box can sit between them. */}
      <div
        className={cn(
          "contents lg:flex lg:flex-col lg:justify-between lg:gap-8 lg:self-stretch",
          flip && "lg:order-2",
        )}
      >
        <div className="order-1">{heading}</div>
        {/* Rows sit at the foot of the room kept for them, so an open body
            pushes the rows above it up, as on Calendly. A pointer or focus
            on them holds the turn. */}
        <ol
          ref={listRef}
          className="order-3 flex flex-col justify-end"
          style={{ minHeight: listHeight }}
          onPointerEnter={(event) => event.pointerType === "mouse" && setResting(true)}
          onPointerLeave={(event) => event.pointerType === "mouse" && setResting(false)}
          onFocus={() => setResting(true)}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) setResting(false);
          }}
        >
          {items.map((item, i) => {
            const isActive = i === active;
            const bodyId = `${id}-row-${i}`;
            return (
              <li key={item.title} className="relative border-b border-slate-900/10 first:border-t">
                <h3>
                  <button
                    type="button"
                    onClick={() => pick(i)}
                    aria-expanded={isActive}
                    aria-controls={bodyId}
                    className={cn(
                      TYPE.item,
                      "flex w-full items-center gap-3 py-4 text-left transition-colors",
                      isActive ? "text-ink" : "text-ink-meta hover:text-ink",
                    )}
                  >
                    <span aria-hidden="true" className="shrink-0 [&>svg]:size-5">
                      {item.icon}
                    </span>
                    {item.title}
                  </button>
                </h3>
                {/* The open row's body, its height eased open; a closed one
                    is inert, so its link takes no focus. */}
                <div
                  id={bodyId}
                  inert={!isActive}
                  className={cn(
                    "grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none",
                    isActive ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                  )}
                >
                  <div className="overflow-hidden">
                    {/* The arrow is centred on the body beside it: at its
                        foot it sat apart from the text (the user's catch). */}
                    <div
                      data-body
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6 pb-5"
                    >
                      <p className="text-ink-meta text-pretty">{item.body}</p>
                      {/* Its own way in, as each of Calendly's rows has. */}
                      <Link
                        href={item.href}
                        aria-label={`Open ${item.title}`}
                        className="text-ink grid size-9 place-items-center rounded-lg bg-slate-900/[0.05] transition-colors hover:bg-slate-900/[0.1]"
                      >
                        <ArrowUpRightIcon aria-hidden="true" className="size-4" />
                      </Link>
                    </div>
                  </div>
                </div>
                {/* The open row's line in the feature's colour: it fills over
                    `TURN` while the turns run, and opens the next row when
                    full; full once the reader has picked a row. Keyed by the
                    row, so each turn fills from empty. */}
                {isActive && (
                  <span
                    key={active}
                    aria-hidden="true"
                    className={cn(
                      "absolute inset-x-0 -bottom-px h-0.5 origin-left",
                      !taken && "row-fill",
                    )}
                    style={{
                      background: accent,
                      animationDuration: `${TURN}ms`,
                      animationPlayState: playing ? "running" : "paused",
                    }}
                    onAnimationEnd={() => setActive((at) => (at + 1) % items.length)}
                  />
                )}
              </li>
            );
          })}
        </ol>
      </div>
      <StudioBox
        ground={ground}
        className={cn(
          "order-2 aspect-square w-full max-w-[34rem] justify-self-center lg:max-w-[min(34rem,calc(100svh-8rem))]",
          flip && "lg:order-1",
        )}
      >
        {items.map((item, i) => (
          <Layer key={item.title} shown={i === active}>
            {item.visual}
          </Layer>
        ))}
      </StudioBox>
    </div>
  );
}

/** One scene in the box, scaled to it, faded in while its row is open. */
function Layer({ shown, children }: { shown: boolean; children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  return (
    <div
      ref={box}
      className={cn(
        "absolute inset-0 flex items-center justify-center p-5 transition-opacity duration-500 ease-out motion-reduce:transition-none sm:p-8",
        shown ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    >
      <Fit box={box}>{children}</Fit>
    </div>
  );
}
