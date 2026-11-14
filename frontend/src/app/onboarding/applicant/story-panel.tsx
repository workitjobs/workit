"use client";

import type { ReactNode, Ref } from "react";

import { Logo } from "@/components/logo";

import { Showcase } from "./showcase";

/**
 * Onboarding's left half: the step's question in large type over a lavender
 * wash, as the page's heading. The fields answer it on the right, under the
 * step rail. From `lg` a moving showcase fills the room under the question
 * (./showcase). Below `lg` the panel is a band across the top holding the
 * logo and the question alone, so the first field is not a screen away; the
 * showcase also hides whenever the panel is too short to hold it, and its
 * room then stays empty rather than pulling the question down.
 *
 * NO SCOUT HERE (KAN-732). Scout sat at the panel's foot from `lg`, an
 * avatar, "Your WorkIt job assistant" and a chat bubble that typed a tip on
 * every step. It acted on nothing: no chat, no button, while Scout's own
 * chat is switched off, so it promised an assistant the student could not
 * use. Every tip repeated what the step already says (the "Optional" beside
 * a field, the resume step's "Nothing is saved until…", the practice step's
 * "Nothing you submit… reaches an employer"), and the Claude step's "WorkIt
 * never runs a model" went false once AI read every upload. Before that
 * (KAN-259) the bubble sat over the question and asked it again in other
 * words, so it was not clear who was asking. The question speaks as the
 * page, never as "I": the resume step's "check what I read" read as Scout,
 * and as nobody once Scout went.
 *
 * The question is focused on every change (./onboarding-form), so a screen
 * reader reads it out; `questionKey` changes with it, so each new one fades
 * in, a step's second question included (the resume step's, once its
 * reading is on screen). tabIndex -1 lets it take focus without joining the
 * tab order, and it draws no ring, since nothing can be done to it.
 *
 * From `lg` it fills the window's height and never scrolls: the screen is one
 * window tall and only the fields' column scrolls (./onboarding-form).
 *
 * The wash is the brand violet mixed thin over --color-brand-tint, so it
 * follows the palette rather than adding hexes of its own.
 */
const WASH = [
  "radial-gradient(55% 45% at 15% 90%, color-mix(in oklab, var(--color-brand) 22%, transparent), transparent 70%)",
  "radial-gradient(45% 40% at 90% 10%, color-mix(in oklab, var(--color-brand) 14%, transparent), transparent 70%)",
  "linear-gradient(160deg, var(--color-brand-tint), var(--color-frame))",
].join(", ");

export function StoryPanel({
  questionKey,
  question,
  headingRef,
}: {
  /** Changes whenever the question does: the step, and the resume step's review. */
  questionKey: string;
  question: ReactNode;
  headingRef: Ref<HTMLHeadingElement>;
}) {
  return (
    <aside style={{ background: WASH }} className="overflow-hidden px-6 lg:flex-[5] lg:px-12">
      <div className="flex flex-col gap-6 py-8 lg:h-full lg:gap-10 lg:py-10">
        <Logo size="card" className="self-start lg:h-10" />

        {/* Keyed on the question so each new one fades in. */}
        <h1
          key={questionKey}
          ref={headingRef}
          tabIndex={-1}
          className="animate-fade text-display lg:text-hero text-ink max-w-xl font-normal outline-none [&_strong]:font-bold"
        >
          {question}
        </h1>

        <Showcase className="hidden min-h-0 flex-1 lg:block" />
      </div>
    </aside>
  );
}
