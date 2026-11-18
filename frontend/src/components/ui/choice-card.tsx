import type { ComponentType, ReactNode } from "react";

import { CheckIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

/**
 * One of two or three big answers to a screen's one question, laid side by
 * side (2026-11-17): a large glyph on a tinted tile, a title and a line, and
 * a check badge in the corner once picked. Onboarding's "Do you have a
 * resume?" first; the user found that question's answers, as ChoiceTile
 * rows, small, alike and dull. A ChoiceTile is still the answer for a
 * question with several short picks.
 *
 * Each answer has its own tint (`tone`), so the two read as different
 * paths at a glance, not one list.
 *
 * MOTION, CSS only and still under reduced motion (`motion-safe:`): the card
 * lifts 2px with a shadow under the pointer and its glyph tilts and grows;
 * it squishes a little on press; picked, its edge and wash turn violet, the
 * check badge pops in (`animate-pop`), and the glyph gives one bounce
 * (`animate-pick`, keyed on `pressed`, so it replays on each pick; a pop's
 * fade from nothing read as the tile blinking out). After Duolingo's and
 * Linear's choice cards: a pick should feel like it landed.
 *
 * A toggle button (`aria-pressed`), as ChoiceTile is; the caller lays the
 * cards out (`grid sm:grid-cols-2`) and names the group.
 */
export function ChoiceCard({
  pressed,
  onClick,
  Icon,
  tone,
  title,
  line,
}: {
  pressed: boolean;
  onClick: () => void;
  /** The answer's glyph, drawn large on its tile; it takes a className. */
  Icon: ComponentType<{ className?: string }>;
  /** The tile's tint and the glyph's colour: "bg-brand-tint text-brand". */
  tone: string;
  title: string;
  line: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        // Below sm the glyph sits beside the words, so two stacked cards
        // leave a phone room for the footer; from sm they stand side by
        // side, the glyph on top.
        "group/choice bg-panel rounded-card focus-visible:ring-brand-ring ease-glide relative flex h-full items-center gap-4 border p-4 text-left transition-[border-color,background-color,box-shadow,translate,scale] duration-200 focus-visible:ring-2 focus-visible:outline-none active:scale-[0.98] sm:flex-col sm:items-start sm:gap-5 sm:p-6",
        "hover:shadow-tile motion-safe:hover:-translate-y-0.5",
        pressed
          ? "border-brand bg-brand-tint/40 shadow-[0_0_0_3px_color-mix(in_oklab,var(--color-brand)_14%,transparent)]"
          : "border-border-surface hover:border-ink-meta",
      )}
    >
      {/* The check badge: an empty ring until picked, then a violet disc
          that pops in. */}
      <span
        aria-hidden
        className={cn(
          "absolute top-4 right-4 grid size-6 place-items-center rounded-full border transition-colors duration-200",
          pressed ? "border-brand bg-brand text-on-brand" : "border-border-control bg-panel",
        )}
      >
        {pressed && <CheckIcon className="motion-safe:animate-pop size-3.5" />}
      </span>

      <span
        aria-hidden
        // Keyed on the pick, so the bounce plays each time it is picked.
        key={String(pressed)}
        className={cn(
          "ease-spring grid size-12 shrink-0 place-items-center rounded-2xl transition-transform duration-300 sm:size-14",
          "motion-safe:group-hover/choice:scale-110 motion-safe:group-hover/choice:-rotate-6",
          pressed && "motion-safe:animate-pick",
          tone,
        )}
      >
        <Icon className="size-7" />
      </span>

      <span className="pr-6">
        <span className="text-subtitle text-ink block font-semibold">{title}</span>
        <span className="text-body text-ink-meta mt-1.5 block font-normal">{line}</span>
      </span>
    </button>
  );
}
