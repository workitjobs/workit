"use client";

import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useRef, useSyncExternalStore, type CSSProperties } from "react";

import { whatIs } from "./data";
import { DraftLines } from "./draft-lines";
import { useArrived, useMediaQuery } from "./hooks";
import { CONTAINER } from "./layout-parts";

/**
 * What is WorkIt (KAN-923, after Loopsii's "What is Loopsii", the user's
 * ask, 2026-11-20): right after the hero and the logo strip, a small label
 * on the left and one large statement on the right, of who WorkIt is for
 * and why, in the drafting grid's frame.
 *
 * As the problems' dark band rises over it and zooms in, the statement
 * steps back: it fades to a quarter and shrinks to 96% over the last
 * stretch of its way up (the camera moving in, after Loopsii's statement
 * blurring under its dark card; the user's ask, 2026-11-20). Opacity and a
 * transform string over an offset the browser can express, so it runs off
 * the main thread; no blur, which would stay half on wherever the reader
 * stopped. From lg up and without reduced motion only.
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
  const sectionRef = useRef<HTMLElement>(null);
  const isDesktop = useMediaQuery("(min-width: 64rem)");
  const reduceMotion = useReducedMotion();
  const stepping = isDesktop === true && !reduceMotion;
  // The section's foot from the screen's foot to its top: the band below
  // rises over that stretch.
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["end end", "end start"],
  });
  const fade = useTransform(scrollYProgress, [0.2, 0.9], [1, 0.25]);
  const recede = useTransform(scrollYProgress, [0.2, 0.9], ["scale(1)", "scale(0.96)"]);
  return (
    <section ref={sectionRef} aria-labelledby="what-is-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        {/* The frame stays put while the statement steps back, so its
            side lines keep to the page's rail. */}
        <div className="relative">
          <DraftLines gap="1.5rem" />
          <motion.div
            className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2.4fr)] lg:gap-12"
            style={stepping ? { opacity: fade, transform: recede } : undefined}
          >
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
          </motion.div>
        </div>
      </div>
    </section>
  );
}

const noSubscribe = () => () => {};
