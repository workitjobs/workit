"use client";

import { useEffect, useState } from "react";

/**
 * The room under an element down to the foot of the page's scroll area
 * (`main`), as `--fill-height` on it: `main`'s height less the element's top
 * and the page's 24px foot (`py-6`) and a card's 1px border, less `below`
 * (what the page holds under the element's own border, in px). The top is
 * measured from the start of the page, not the window, so the value holds
 * still while the page scrolls: one that grew as the element's top rose
 * would grow the page with it. Read again when `main` resizes (the window)
 * or the page does (a notice above the element). Returns a callback ref.
 *
 * Used by every page table (`TABLE_FILL`) and Tailor's resume list
 * (components/resume-list.tsx, `ResumeScroll`'s `fill`).
 */
export function useFillPage(on = true, below = 0) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  useEffect(() => {
    const page = el?.closest("main");
    if (!on || !el || !page) return;
    const fit = () => {
      const top =
        el.getBoundingClientRect().top - page.getBoundingClientRect().top + page.scrollTop;
      el.style.setProperty(
        "--fill-height",
        `${Math.round(page.clientHeight - top - 25 - below)}px`,
      );
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(page);
    if (page.firstElementChild) observer.observe(page.firstElementChild);
    return () => observer.disconnect();
  }, [on, el, below]);
  return setEl;
}

/**
 * A page table's scroll box (the table's container, `containerClassName`
 * with `useFillPage` as its `containerRef`): from 672px of page it runs down
 * to the page's foot, never under 320px, and scrolls inside itself on both
 * axes, so the page's search, filters and heading above it stay in view
 * (2026-11-10). The whole page scrolled until then, and the filters left
 * the screen with the first rows. Below 672px (a phone) the page scrolls as
 * one: a box that scrolls inside a scrolling page traps the swipe that
 * reaches its end.
 */
export const TABLE_FILL =
  "@2xl/main:max-h-[max(20rem,var(--fill-height,100svh))] @2xl/main:overflow-y-auto";

/**
 * A page table's heading cell, held at the top of its scroll box while the
 * rows scroll under it: the panel's white, so rows do not show through, and
 * the heading's rule drawn as an inset shadow, since a row's border does not
 * move with a sticky cell. A cell that is also sticky on x (a frozen first
 * column, a ⋯ column) takes `z-3` after this, over both.
 */
export const STICKY_TH =
  "sticky top-0 z-2 bg-panel shadow-[inset_0_-1px_0_var(--color-border-subtle)]";

/**
 * The heading row of a table with `STICKY_TH` cells, on its `TableHeader`:
 * no border of its own, so the cells' inset rule is the only one. With
 * both, the row's border and the cells' rule drew a 2px grey bar under
 * every heading but a frozen one, whose own edge shadow replaced the
 * cell's rule (2026-11-11, the user's "weird horizontal gray bar"). The
 * row's border also stays behind while the rows scroll; the cells' does
 * not.
 */
export const STICKY_HEAD = "[&_tr]:border-b-0";

/** A frozen heading's two edges at once: the heading's rule under it and
 *  the frozen column's edge at its right. One `shadow` replaces another, so
 *  a frozen heading that took only its edge lost its rule. */
export const STICKY_TH_FROZEN =
  "shadow-[inset_0_-1px_0_var(--color-border-subtle),1px_0_0_var(--color-border-subtle)]";
