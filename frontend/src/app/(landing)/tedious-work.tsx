"use client";

import { useRef, useSyncExternalStore, type CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { tediousWork } from "./data";
import { useArrived } from "./hooks";
import { CONTAINER, PANEL, PANEL_INSET, TYPE } from "./layout-parts";

/**
 * The tedious work in the way (KAN-923, after Loopsii's "Too many things
 * pulling you away", the user's ask, 2026-11-20): a dark band after What
 * is WorkIt, its heading in two halves, "Too much tedious work" at the top
 * left and "between you and the job you want" at the foot right, and
 * between them, in large brackets, the thoughts a job seeker has in a week
 * of applying, as pills. It is the page's one dark band before the footer:
 * the search before WorkIt, the mood the bright product sections answer.
 * Ink, never a feature's colour (`.tedious-ground` in landing.css).
 *
 * The pills pop in one after another as the band arrives, in time, not
 * scrubbed by the scroll (`useArrived`, `.thought` in landing.css), and
 * rest; the server's HTML has no `data-arrived`, so without script and
 * with reduced motion they show at once. Screen readers get the heading
 * whole (`sr-only`) and the thoughts as a list; the two visual halves are
 * hidden from them.
 */
export function TediousWork() {
  const ref = useRef<HTMLUListElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(ref, mounted, { margin: "0px 0px -25% 0px" });
  const { start, end, thoughts } = tediousWork;
  return (
    <section aria-labelledby="tedious-title" className={cn(PANEL_INSET, "py-2")}>
      <div className={cn(PANEL, "tedious-ground relative isolate overflow-hidden py-20 sm:py-28")}>
        <div className={CONTAINER}>
          <h2 id="tedious-title" className="sr-only">
            {start} {end}
          </h2>
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:gap-6">
            <p
              aria-hidden="true"
              className={cn(TYPE.product, "font-display text-white lg:self-start")}
            >
              {start}
            </p>
            <div className="flex items-center gap-2 sm:gap-3 lg:row-span-2">
              <span aria-hidden="true" className="tedious-bracket font-display">
                (
              </span>
              <ul
                ref={ref}
                data-arrived={mounted ? String(arrived) : undefined}
                className="flex max-w-[28rem] flex-wrap justify-center gap-2 sm:gap-2.5"
              >
                {thoughts.map((thought, i) => (
                  <li
                    key={thought}
                    className="thought text-ink rounded-full bg-white px-3.5 py-2 text-[15px] font-medium shadow-[0_10px_24px_-12px_rgb(0_0_0/0.6)]"
                    style={{ "--c": i } as CSSProperties}
                  >
                    {thought}
                  </li>
                ))}
              </ul>
              <span aria-hidden="true" className="tedious-bracket font-display">
                )
              </span>
            </div>
            <p
              aria-hidden="true"
              className={cn(
                TYPE.product,
                "font-display text-right text-white lg:col-start-3 lg:row-start-2 lg:self-end",
              )}
            >
              {end}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

const noSubscribe = () => () => {};
