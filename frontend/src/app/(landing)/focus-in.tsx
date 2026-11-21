"use client";

import * as React from "react";

/**
 * A block whose pieces rise as it arrives, each from behind its own foot,
 * a little apart (`.focus-in` in landing.css): Pricing's FAQ rows and
 * closing band. A `SectionHeading` rises on its own now and needs no
 * wrapper. It was a rise out of a blur until 2026-11-21. An observer marks it
 * `data-focus="wait"` while it is below the screen and `"in"` once it is
 * well inside, so it plays again after the visitor scrolls back above it.
 * The server's HTML has no mark, so the heading shows before the script
 * runs; below lg and with reduced motion it is never marked, like every
 * scene on the page.
 *
 * Not a scroll-driven CSS animation (`view()`): under a pin, Chrome placed
 * the heading's view timeline hundreds of pixels from where the heading
 * stood, and it stayed blurred for most of the pinned stretch.
 */
export function FocusIn({ children }: { children: React.ReactNode }) {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const el = ref.current;
    if (
      !el ||
      !window.matchMedia("(min-width: 64rem)").matches ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    // In once well inside the screen; back to waiting only once wholly
    // below it. One observer did both at the arrival line, so a heading
    // vanished in full view when the reader scrolled back a little.
    const show = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) el.dataset.focus = "in";
      },
      { rootMargin: "0px 0px -12% 0px" },
    );
    const hide = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting && entry.boundingClientRect.top > 0) el.dataset.focus = "wait";
    });
    // Already on screen: show it as it is.
    if (el.getBoundingClientRect().top > window.innerHeight * 0.88) el.dataset.focus = "wait";
    show.observe(el);
    hide.observe(el);
    return () => {
      show.disconnect();
      hide.disconnect();
    };
  }, []);
  return (
    <div ref={ref} className="focus-in">
      {children}
    </div>
  );
}
