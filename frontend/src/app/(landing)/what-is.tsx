"use client";

import { useRef, useSyncExternalStore, type CSSProperties } from "react";

import { whatIs } from "./data";
import { DraftLines } from "./draft-lines";
import { useArrived } from "./hooks";
import { CONTAINER } from "./layout-parts";

/**
 * What is WorkIt (KAN-923, after Loopsii's "What is Loopsii", the user's
 * ask, 2026-11-20): right after the hero and the logo strip, a small label
 * on the left and one large statement on the right, of who WorkIt is for
 * and why, in the drafting grid's frame.
 *
 * The statement reads in word by word as it arrives, in time, not scrubbed
 * by the scroll (`useArrived`; `.word-reveal` in landing.css): each word
 * comes up from a faint grey a little after the one before. The server's
 * HTML has no `data-arrived`, so without script, and with reduced motion,
 * the words show at once.
 */
export function WhatIs() {
  const ref = useRef<HTMLParagraphElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(ref, mounted, { margin: "0px 0px -25% 0px" });
  const words = whatIs.statement.split(" ");
  return (
    <section aria-labelledby="what-is-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <div className="relative grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2.4fr)] lg:gap-12">
          <DraftLines gap="1.5rem" />
          <h2 id="what-is-title" className="text-ink-meta font-sans text-[15px] font-medium">
            {whatIs.label}
          </h2>
          <p
            ref={ref}
            data-arrived={mounted ? String(arrived) : undefined}
            className="word-reveal font-display text-ink text-[1.625rem] leading-[1.25] font-medium tracking-[-0.02em] text-pretty sm:text-[2rem] lg:text-[2.375rem]"
          >
            {words.map((word, i) => (
              <span key={i} style={{ "--w": i } as CSSProperties}>
                {word}{" "}
              </span>
            ))}
          </p>
        </div>
      </div>
    </section>
  );
}

const noSubscribe = () => () => {};
