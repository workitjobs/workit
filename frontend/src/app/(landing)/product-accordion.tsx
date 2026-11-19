"use client";

import { ArrowUpRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";

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

/** Where the section pins: from lg up, on a screen tall enough to hold the
 *  heading, the rows and the box at once (`.product-track` and
 *  `.product-stage` in landing.css use the same query). */
const PIN_QUERY = "(min-width: 64rem) and (min-height: 40rem)";

/**
 * A product section's heading, rows and picture (product-sections.tsx,
 * KAN-923), after Calendly's product sections. Where it pins (`PIN_QUERY`)
 * the whole section stops in the middle of the screen under the header,
 * heading, rows and box together, and the scroll opens one row at a time:
 * each row has its own stretch of scroll (`.product-track`, 45svh a row),
 * the open row shows its body and its arrow link to its deep dive, a line
 * in the feature's colour fills along its foot as the scroll moves through
 * its stretch, and the box shows its still scene, swapping with a fade.
 * Once the last row's stretch ends, the section scrolls away. A click on a
 * row's title scrolls to that row's stretch. The scroll picks the row; the
 * swap plays in time ("scroll cues, time plays"), and only the line tracks
 * the scroll.
 *
 * It replaced a sticky heading over rows that scrolled up beneath it, which
 * the user found broken: the section went to the top of the screen, then
 * the list moved inside it, and a row's title was cut by the heading's
 * foot. Calendly's section stops as one block.
 *
 * Below lg, and on a screen too short to pin, nothing sticks: a tap on a
 * row's title opens it and shows its scene; below lg the box sits between
 * the heading and the rows (one tree, `display: contents`).
 *
 * The open row is worked out on scroll only (a passive listener, one read
 * of the track's rect per frame at most), and only while the section is
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
  /** The feature's colour: the open row's line. */
  accent: string;
  /** Box on the left from lg up, so the sections alternate sides. */
  flip?: boolean;
}) {
  const [active, setActive] = useState(0);
  const pinned = useMediaQuery(PIN_QUERY) === true;
  const trackRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLOListElement>(null);
  const id = useId();
  // The rows' height with the longest body open, so the column, and the
  // pinned block centred on it, keep one height whichever row is open:
  // grown and shrunk with each row, the block shifted by up to 10px.
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

  // Where it pins, the open row follows how far the track has scrolled
  // past the point where the stage sticks; the line under the open row
  // reads the same progress (`--row-progress`, 0 to 1 within the row).
  useEffect(() => {
    const track = trackRef.current;
    const stage = stageRef.current;
    if (!pinned || !track || !stage) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const stickAt = parseFloat(getComputedStyle(stage).top) || 0;
      const travel = track.offsetHeight - stage.offsetHeight;
      if (travel <= 0) return;
      const progress = Math.min(
        1,
        Math.max(0, (stickAt - track.getBoundingClientRect().top) / travel),
      );
      const row = Math.min(items.length - 1, Math.floor(progress * items.length));
      setActive(row);
      track.style.setProperty("--row-progress", String(progress * items.length - row));
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
    near.observe(track);
    return () => {
      near.disconnect();
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, [pinned, items.length]);

  const pick = (i: number) => {
    const track = trackRef.current;
    const stage = stageRef.current;
    if (!pinned || !track || !stage) return setActive(i);
    // To the start of the row's stretch, a little in, so it is the open one.
    const stickAt = parseFloat(getComputedStyle(stage).top) || 0;
    const travel = track.offsetHeight - stage.offsetHeight;
    const trackTop = window.scrollY + track.getBoundingClientRect().top;
    scrollPageTo(trackTop - stickAt + ((i + 0.05) / items.length) * travel);
  };

  return (
    <div
      ref={trackRef}
      className="product-track"
      style={{ "--rows": items.length } as CSSProperties}
    >
      <div ref={stageRef} className="product-stage">
        <div className="grid w-full gap-y-8 lg:grid-cols-2 lg:items-center lg:gap-x-16 lg:gap-y-0">
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
            {/* Rows sit at the foot of the room kept for them, so an open
                body pushes the rows above it up, as on Calendly. */}
            <ol
              ref={listRef}
              className="order-3 flex flex-col justify-end"
              style={pinned ? { minHeight: listHeight } : undefined}
            >
              {items.map((item, i) => {
                const isActive = i === active;
                const bodyId = `${id}-row-${i}`;
                return (
                  <li
                    key={item.title}
                    className="relative border-b border-slate-900/10 first:border-t"
                  >
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
                    {/* The open row's body, its height eased open; a closed
                        one is inert, so its link takes no focus. */}
                    <div
                      id={bodyId}
                      inert={!isActive}
                      className={cn(
                        "grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none",
                        isActive ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                      )}
                    >
                      <div className="overflow-hidden">
                        <div
                          data-body
                          className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-x-6 pb-5"
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
                    {/* The open row's line in the feature's colour: it fills
                        with the scroll through the row's stretch where the
                        section pins, and is full elsewhere. */}
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className="absolute inset-x-0 -bottom-px h-0.5 origin-left"
                        style={{
                          background: accent,
                          transform: pinned ? "scaleX(var(--row-progress, 0))" : undefined,
                        }}
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
      </div>
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
