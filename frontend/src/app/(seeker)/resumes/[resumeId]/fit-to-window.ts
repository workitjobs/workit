"use client";

import { useEffect, useState } from "react";

/**
 * A column's height cap, as `--fit-height` on it: the window below its
 * top, less a 24px foot. The review's panel and rail stick at it, and the
 * desk takes it as its height, so the pages scroll inside the desk
 * (`DESK_SCROLL` in ./slim-bar.ts). Read again on any scroll (the page
 * scrolls in `main`, not the window, so the listener captures) and on
 * resize, once a frame. Before the page scrolls the column's top sits
 * under the title row; stuck, at its `top`; a fixed cap fitted one and not
 * the other. Its top is read no higher than where it sticks: at the page's
 * end the grid pushes a sticky column up past that, and reading that top
 * grew the cap, so the panel kept growing as the page scrolled. Never
 * under 240px, so a short window still shows the panel's top.
 */
export function useFitToWindow(foot = 24) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (!el) return;
    let frame = 0;
    const fit = () => {
      frame = 0;
      const stuck =
        (el.closest("main")?.getBoundingClientRect().top ?? 0) +
        (parseFloat(getComputedStyle(el).top) || 0);
      const room = window.innerHeight - Math.max(el.getBoundingClientRect().top, stuck) - foot;
      el.style.setProperty("--fit-height", `${Math.max(240, Math.round(room))}px`);
    };
    const queue = () => {
      if (!frame) frame = requestAnimationFrame(fit);
    };
    fit();
    document.addEventListener("scroll", queue, { capture: true, passive: true });
    window.addEventListener("resize", queue);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("scroll", queue, { capture: true });
      window.removeEventListener("resize", queue);
    };
  }, [el, foot]);
  return setEl;
}
