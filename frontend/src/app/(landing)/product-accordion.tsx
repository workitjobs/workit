"use client";

import { ArrowUpRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Fit } from "./fit";
import { useMediaQuery } from "./hooks";
import { StudioBox, TYPE } from "./layout-parts";
import { scrollPageTo } from "./smooth-scroll";

export type ProductItem = {
  title: string;
  body: string;
  /** The row's mark, rendered by the server (a feature page section's icon). */
  icon: ReactNode;
  /** Its deep dive on the feature page (`deepDiveAnchor`). */
  href: string;
  visual: ReactNode;
};

/** Tailwind's lg: the rows scroll under a sticky heading from here up. */
const DESKTOP_QUERY = "(min-width: 64rem)";
/** How far under the sticky heading's foot a row counts as active, in px. */
const ACTIVE_SLACK = 24;

/**
 * A product section's heading, rows and picture (product-sections.tsx,
 * KAN-923), after Calendly's product sections, which the user pointed
 * back to: from lg up the heading sticks under the header on the white
 * page, the rows scroll up beneath it, and the row just under its foot is
 * the active one, full strength, the others faded to 25%; the framed box
 * beside them sticks too and shows the active row's still scene, swapping
 * with a fade. The scroll picks the row; the swap plays in time ("scroll
 * cues, time plays"), and nothing is scrubbed. Each row has its own arrow
 * link to its deep dive on the feature page, as each of Calendly's rows
 * has one, in place of the one "Explore" link by the heading. A click on a
 * row's title scrolls it to the active line.
 *
 * Below lg nothing sticks: the heading, then the box, then the rows, all at
 * full strength; a tap on a title shows its scene, and the open row carries
 * the feature's colour along its foot. The order comes from the grid with
 * `display: contents` on the left column, so one tree serves both.
 *
 * The active row is worked out on scroll only (a passive listener, one
 * read of a few rects per frame at most), and only while the section is
 * near the screen: nothing runs at rest.
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
  /** The feature's colour: the open row's rule below lg. */
  accent: string;
  /** Box on the left from lg up, so the sections alternate sides. */
  flip?: boolean;
}) {
  const [active, setActive] = useState(0);
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const rootRef = useRef<HTMLDivElement>(null);
  const headRef = useRef<HTMLDivElement>(null);
  const rowRefs = useRef<(HTMLLIElement | null)[]>([]);
  const boxRef = useRef<HTMLDivElement>(null);
  // From lg up the last row is at least as tall as the box below the
  // heading, so the box, the heading and the last row leave together.
  const [tail, setTail] = useState(0);

  // From lg up, the active row is the last one whose top has reached the
  // sticky heading's foot. Watched only while the section is near.
  useEffect(() => {
    const root = rootRef.current;
    if (!isDesktop || !root) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const line = (headRef.current?.getBoundingClientRect().bottom ?? 0) + ACTIVE_SLACK;
      let next = 0;
      rowRefs.current.forEach((row, i) => {
        if (row && row.getBoundingClientRect().top <= line) next = i;
      });
      setActive(next);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    const near = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          window.addEventListener("scroll", onScroll, { passive: true });
          measure();
        } else window.removeEventListener("scroll", onScroll);
      },
      { rootMargin: "50% 0px" },
    );
    near.observe(root);
    return () => {
      near.disconnect();
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, [isDesktop]);

  useEffect(() => {
    const box = boxRef.current;
    const head = headRef.current;
    if (!isDesktop || !box || !head) return;
    const measure = () => setTail(Math.max(0, box.offsetHeight - head.offsetHeight));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    observer.observe(head);
    return () => observer.disconnect();
  }, [isDesktop]);

  const pick = (i: number) => {
    if (!isDesktop) return setActive(i);
    const row = rowRefs.current[i];
    const head = headRef.current;
    if (!row || !head) return;
    const line = head.getBoundingClientRect().bottom + ACTIVE_SLACK / 2;
    scrollPageTo(window.scrollY + row.getBoundingClientRect().top - line + 1);
  };

  const renderRow = (item: ProductItem, i: number) => {
    const isActive = i === active;
    const isLast = i === items.length - 1;
    return (
      <li
        key={item.title}
        ref={(el) => {
          rowRefs.current[i] = el;
        }}
        aria-current={isActive || undefined}
        className={cn(
          "relative grid grid-cols-[minmax(0,1fr)_auto] content-start gap-x-6 border-b border-slate-900/10 py-6 transition-opacity duration-300 motion-reduce:transition-none lg:min-h-[14rem] lg:py-8",
          !isActive && "lg:opacity-25",
        )}
        style={isLast && tail ? { minHeight: tail } : undefined}
      >
        <h3 className="col-start-1">
          <button
            type="button"
            onClick={() => pick(i)}
            className={cn(
              TYPE.item,
              "flex w-full items-center gap-3 text-left transition-colors",
              isActive ? "text-ink" : "text-ink-meta hover:text-ink",
            )}
          >
            <span aria-hidden="true" className="text-ink shrink-0 [&>svg]:size-5">
              {item.icon}
            </span>
            {item.title}
          </button>
        </h3>
        <p className="text-ink-meta col-start-1 mt-2 text-pretty">{item.body}</p>
        {/* Its own way in, as each of Calendly's rows has. */}
        <Link
          href={item.href}
          aria-label={`Open ${item.title}`}
          className="text-ink col-start-2 row-span-2 row-start-1 grid size-9 place-items-center self-center rounded-lg bg-slate-900/[0.05] transition-colors hover:bg-slate-900/[0.1]"
        >
          <ArrowUpRightIcon aria-hidden="true" className="size-4" />
        </Link>
        {/* Below lg the open row carries the feature's colour. */}
        {isActive && (
          <span
            aria-hidden="true"
            className="absolute inset-x-0 -bottom-px h-0.5 rounded-full lg:hidden"
            style={{ background: accent }}
          />
        )}
      </li>
    );
  };

  return (
    <div
      ref={rootRef}
      className="grid gap-y-8 lg:grid-cols-2 lg:items-start lg:gap-x-16 lg:gap-y-0"
    >
      {/* The heading and the rows: one column from lg up, so the heading
          can stick over the rows; below lg its children join the grid so
          the box can sit between them. */}
      <div className={cn("contents lg:block", flip && "lg:order-2")}>
        {/* The heading sticks over every row but the last: its sticky
            area ends where the last row begins, so the heading and the last
            row leave together, and the last row's height (`tail`) lets the
            box leave with them. Before this the box left 300px early and
            the heading floated over blank page. */}
        <div className="contents lg:block">
          <div
            ref={headRef}
            className="order-1 bg-white pb-6 lg:sticky lg:top-[5.5rem] lg:z-10 lg:pt-2"
          >
            {heading}
            <hr className="mt-8 border-slate-900/10" />
          </div>
          <ol className="order-3">{items.slice(0, -1).map((item, i) => renderRow(item, i))}</ol>
        </div>
        <ol start={items.length} className="order-4">
          {renderRow(items[items.length - 1], items.length - 1)}
        </ol>
      </div>
      <StudioBox
        ref={boxRef}
        ground={ground}
        className={cn(
          "order-2 aspect-square w-full max-w-[34rem] justify-self-center lg:sticky lg:top-[5.5rem] lg:max-h-[calc(100svh-7rem)]",
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

/** One scene in the box, scaled to it, faded in while its row is active. */
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
