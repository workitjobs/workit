"use client";

import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { Fragment, useRef, useSyncExternalStore, type CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { AppIcon } from "./app-icon";
import { whatIs } from "./data";
import { DraftLines } from "./draft-lines";
import { useArrived, useMediaQuery } from "./hooks";
import { CONTAINER, TYPE } from "./layout-parts";

/**
 * What is WorkIt (KAN-923, after Loopsii's "What is Loopsii", the user's
 * ask, 2026-11-20): right after the hero and the logo strip, WorkIt's app
 * icon in glass, large, on the left (`AppIcon`; a bare grey label read as
 * plain text, the user's catch), and on the right the question "What is
 * WorkIt?" over its answer: one large line of who WorkIt is for, then one
 * smaller line on how, in the drafting grid's frame. It was one large
 * paragraph of six lines under a small grey label beside it, which read as
 * a wall of text with the label oddly placed (the user's catch,
 * 2026-11-20).
 *
 * As the problems' grey band rises over it and zooms in, the statement
 * steps back: it fades to a quarter and shrinks to 96% over the last
 * stretch of its way up (the camera moving in, after Loopsii's statement
 * blurring under its dark card; the user's ask, 2026-11-20). Opacity and a
 * transform string over an offset the browser can express, so it runs off
 * the main thread; no blur, which would stay half on wherever the reader
 * stopped. From lg up and without reduced motion only.
 *
 * **Its entrance, in the hero's vocabulary, with no fades** (2026-11-21,
 * the user's ask for a proper transition here): as the section arrives its
 * frame draws itself (`DraftLines`), the app icon pops in as the grid's
 * ink squares do, its name rises from behind its own foot, and the answer
 * rises word by word the same way, the large line and then the smaller
 * one (`.what-is-mark`, `.word-rise` in landing.css). In time, not
 * scrubbed by the scroll (`useArrived`). A clip and a translate, never
 * opacity: the words came up from a faint grey before, a fade. The
 * server's HTML has no `data-arrived`, so without script, and with reduced
 * motion, everything shows at once.
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
  const detail = whatIs.detail.split(" ");
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
            className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2.4fr)] lg:gap-12"
            style={stepping ? { opacity: fade, transform: recede } : undefined}
          >
            {/* WorkIt's app icon as a floating slab of glass (app-icon.tsx)
                with its name under it, as on a home screen, centred in its
                column both ways: across, between the frame's side line
                (1.5rem outside the column) and the words, so the column's
                padding is that 1.5rem (the user's asks, 2026-11-20). Beside
                the name below lg. */}
            <div
              data-arrived={mounted ? String(arrived) : undefined}
              className="what-is-mark flex items-center gap-4 lg:flex-col lg:justify-center lg:gap-3 lg:pl-6"
            >
              <AppIcon />
              <h2
                id="what-is-title"
                className="text-ink-meta text-lg font-medium tracking-[-0.01em] lg:text-center lg:text-xl"
              >
                {whatIs.label}
              </h2>
            </div>
            {/* The answer: one large line, then one smaller line on how.
                One long paragraph at the large size read as a wall of text
                (the user's catch, 2026-11-20). */}
            <div className="lg:py-4">
              <p
                ref={ref}
                data-arrived={mounted ? String(arrived) : undefined}
                className="word-rise font-display text-ink text-[2rem] leading-[1.1] font-medium tracking-[-0.025em] text-balance sm:text-[2.5rem] lg:text-[3rem]"
              >
                {words.map((word, i) => (
                  <Fragment key={i}>
                    <span style={{ "--w": i } as CSSProperties}>{word}</span>{" "}
                  </Fragment>
                ))}
              </p>
              <p
                data-arrived={mounted ? String(arrived) : undefined}
                className={cn(TYPE.lead, "word-rise text-ink-meta mt-6 max-w-2xl text-pretty")}
              >
                {detail.map((word, i) => (
                  <Fragment key={i}>
                    <span style={{ "--w": words.length + 2 + i } as CSSProperties}>
                      {word}
                    </span>{" "}
                  </Fragment>
                ))}
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

const noSubscribe = () => () => {};
