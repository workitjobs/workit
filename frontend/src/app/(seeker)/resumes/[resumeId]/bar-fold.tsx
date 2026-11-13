"use client";

import { useRef, useState, type ReactElement, type ReactNode } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/shadcn/tooltip";

/**
 * How the slim bar folds as it narrows, after Google Docs' toolbar: one row,
 * never two (KAN-576, KAN-799). Words go first, least needed first, each
 * control keeping its glyph, its name and a tooltip (`FoldButton`); then
 * whole controls leave the row for More (⋯) at its end, which lists only
 * what has left. The bar folds by measure, not by fixed widths:
 * `useFoldToFit` (./toolbar.tsx) takes one step at a time until the row is no
 * wider than the bar, after every change of what the row holds and of the
 * bar's width, before paint. Each box names the step that folds it:
 * `data-word-at` (its word goes, `FOLD.word`) or `data-away-at` (it leaves,
 * `FOLD.away`).
 *
 * The idle bar's steps (`FOLD.idle`): Cut From Resume's word, Add
 * Experiences', Fit to One Page's; then Cut From Resume, the zoom and Add
 * Experiences leave. Undo, Redo, Fit to One Page and the side panel's button
 * never leave: the panel's button (KAN-586) is the only way back to a closed
 * panel, which holds Sections and Format as tabs.
 *
 * With a line open (`FOLD.line`): the zoom leaves, then the line's two
 * arrows. Until KAN-586 the open line also had its size, bold, italic, its
 * other tools (Original, GPA, Coursework, Add Bullet, Hide, Edit Header) and
 * Done, each with a step here.
 *
 * Fixed widths came first (KAN-576): container-query steps measured by hand
 * on the editor's own page, which folded Tailor's bar, with fewer buttons,
 * early, and needed measuring again for every button or word added. A bar
 * with a line open had none and wrapped to a second row. The idle bar's real
 * buttons wait for the first render, which only the browser runs, so the
 * server's first paint never needed CSS steps; only the skeletons have one.
 *
 * Classes are whole strings, so Tailwind finds them in this file.
 */
export const FOLD = {
  /** On a word inside a box whose `data-word-at` step has come. */
  word: "in-data-[words-folded]:sr-only",
  /** On a box whose `data-away-at` step has come. */
  away: "data-[away]:hidden",
  /** More, once any box has left. */
  more: "hidden in-data-[some-away]:flex",
  idle: {
    cutWordAt: 1,
    experiencesWordAt: 3,
    fitWordAt: 4,
    cutAt: 5,
    zoomAt: 6,
    experiencesAt: 8,
  },
  line: {
    toolWordsAt: 1,
    zoomAt: 2,
    toolAt: { extra: 3, move: 4, main: 5 },
  },
  /** The panels' skeletons, before the first render, on a narrow bar. */
  skeletonAway: "@max-[30rem]/bar:hidden",
} as const;

/** The phone editor's two rows (./phone.tsx) fold the same way, with
 *  nothing to move to More (KAN-586). The toolbar folds Add Experiences'
 *  word first, then Fit's, so a 390px phone keeps "Fit" beside the stack
 *  glyph; Cut, Zoom and the panel's button are glyphs at every width. The
 *  title row folds Download's word under 22rem, to keep room for the name.
 *  The phone kept Format and Zoom as worded buttons and Download at the
 *  toolbar's end until the toolbar became the desktop's. */
export const PHONE_FOLD = {
  experiencesWord: "@max-[34rem]/bar:sr-only",
  fitWord: "@max-[26rem]/bar:sr-only",
  downloadWord: "@max-[22rem]/title:sr-only",
} as const;

/** `sr-only` draws the word 1px wide. */
const folded = (word: HTMLElement | null) => (word?.offsetWidth ?? 0) <= 1;

/**
 * A bar button whose word folds away (`fold`, one of `FOLD`'s word steps).
 * Its name is the word, as `aria-label` too, so a folded button keeps it. A
 * folded button names itself in a tooltip, since its glyph alone may not
 * say what it does; `hint`, what a `title` said before, shows over the
 * word as well. The tooltip opens only while the word is hidden when there
 * is no hint: over the word it said the same thing twice.
 *
 * `render` is the button itself, a `Button` or a menu's trigger, so the
 * tooltip adds no element to the row.
 */
export function FoldButton({
  label,
  icon,
  fold,
  hint,
  after,
  disabled,
  render,
}: {
  label: string;
  icon: ReactNode;
  fold: string;
  hint?: string;
  /** After the word: Download's caret. */
  after?: ReactNode;
  disabled?: boolean;
  render: ReactElement;
}) {
  const word = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [tip, setTip] = useState("");
  return (
    <Tooltip
      open={open}
      onOpenChange={(next) => {
        const text = folded(word.current) ? (hint ? `${label}: ${hint}` : label) : (hint ?? "");
        // Kept while closing, so the tooltip fades out with its words
        if (next) setTip(text);
        setOpen(next && text !== "");
      }}
    >
      <TooltipTrigger disabled={disabled} aria-label={label} render={render}>
        {icon}{" "}
        <span ref={word} className={fold}>
          {label}
        </span>
        {after}
      </TooltipTrigger>
      <TooltipContent>{tip}</TooltipContent>
    </Tooltip>
  );
}
