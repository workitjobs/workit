import { useEffect, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * The resume list every resume picker draws (KAN-406): the student's
 * resumes in one scroll. Each picker draws its own cards inside it, each
 * with a radio (app/(seeker)/jobs/resume-picker.tsx). It drew a heading
 * per type (KAN-404) until 2026-11-10, when the pickers went flat as the
 * Resumes page had (KAN-766).
 */

/** The resume types, named as the Resumes page's Type filter is. */
export const RESUME_TYPES = [
  { value: "uploaded", label: "Uploaded" },
  { value: "generated", label: "Generated" },
  { value: "tailored", label: "Tailored" },
] as const;

export type ResumeType = (typeof RESUME_TYPES)[number]["value"];

/** The search's words, lowercased. */
export function searchWords(query: string): string[] {
  return query.trim().toLowerCase().split(/\s+/).filter(Boolean);
}

/** Whether every word is in the text: "acme intern" finds "Intern at Acme". */
export function matches(text: string, words: string[]): boolean {
  const lower = text.toLowerCase();
  return words.every((word) => lower.includes(word));
}

/** The list's 4px head (with the first card's 8px margin, the 12px its
 *  sides have), five cards of 52px each with its 8px top margin
 *  (`RESUME_ROW`), and the list's 12px foot: 316px. A card or gap that
 *  changes size changes this too. A list of fewer cards stops short of
 *  it. */
const FIVE_ROWS = "max-h-[calc(0.25rem+5*3.75rem+0.75rem)]";

/** `fill`'s cap: the room `useFillPage` measured, never under `FIVE_ROWS`,
 *  which also holds until it has measured (the server's render). */
const FILL_PAGE = "max-h-[max(calc(0.25rem+5*3.75rem+0.75rem),var(--fill-height,0px))]";

/**
 * The list's one scroll, five cards high, not the shared
 * `max-h-scroll-box` (320px) that Top Matches uses, so a card is never cut
 * at the foot. With `fill`
 * (a page's list: the Resumes page, KAN-434, and Tailor's Pick a Resume,
 * KAN-576) it runs down to the foot of the page instead: five cards left
 * half a laptop screen empty under it, and cut the last card in half. The
 * five-card cap is a dialog's. `below` is what the page holds under the
 * list's own border, in px (Tailor's card: its padding and border).
 */
export function ResumeScroll({
  label,
  fill = false,
  below = 0,
  children,
}: {
  label?: string;
  fill?: boolean;
  below?: number;
  children: ReactNode;
}) {
  const fit = useFillPage(fill, below);
  return (
    // pt-1 and pb-3: the first and last cards' room, which also leaves a
    // card's lift under the pointer room the scroll would clip.
    <ul
      ref={fill ? fit : undefined}
      role="list"
      aria-label={label}
      className={cn(fill ? FILL_PAGE : FIVE_ROWS, "flex flex-col overflow-y-auto px-3 pt-1 pb-3")}
    >
      {children}
    </ul>
  );
}

/**
 * The room under the list, as `--fill-height` on it: the page's scroll
 * area (`main`) below the list's top, less the page's 24px foot (`py-6`)
 * and the card's 1px border. The top is measured from the start of the
 * page, not the window, so the cap holds still while the page scrolls: a
 * cap that grew as the list's top rose would grow the page with it. Read
 * again when `main` resizes (the window) or the page does (an upload's
 * note above the list).
 */
function useFillPage(on: boolean, below: number) {
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
