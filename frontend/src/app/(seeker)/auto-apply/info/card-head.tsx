import type { ReactNode } from "react";

import { GLYPH_TILE } from "@/components/ui/option-row";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn } from "@/lib/cn";

import { SECTION_CARD } from "../../profile/field-styles";
import { INFO_SECTIONS, type InfoSectionKey } from "./sections";

/**
 * An Application Info card's own classes: the section card's padding, and
 * everything under the head starts where the title does (the tile's 40px
 * and the 12px gap), so the card has one left edge of text and the glyph
 * hangs beside it. With the body at the card's edge, the facts lined up
 * under the tile and the title stood 52px in: two left edges in one card.
 * Not on a phone, where 52px is a sixth of the width.
 */
export const INFO_CARD = cn(SECTION_CARD, "@xl/main:*:not-first:ml-13");

/**
 * The head of every Application Info card (2026-11-23): the part's glyph
 * on a grey tile, its title over its description, and the card's own
 * actions at the right. It is the option row's shape
 * (components/ui/option-row.tsx, Profile's Application Info card): a
 * glyph on a tile beside a name over one line.
 *
 * THE GLYPH IS THE MENU'S (./sections.ts), so the eye finds a card from
 * its menu row by shape, before it reads a word. The six cards were a
 * title and grey text alone, which the user found a wall of text on white.
 * Grey, not brand: it says what the card is, and brand is for what is on
 * or picked, as the open row in the menu beside it.
 *
 * ONE HEAD FOR ALL SIX, in every state. Transcript and Writing Samples
 * drew a centred empty state in the card's place while they held nothing,
 * a second look among four cards with a title at the left; they keep this
 * head now and put their first action in the body, as Workday Sign-Up
 * does.
 *
 * `under` goes below the description (the answered count). The actions sit
 * in the tile's height, so a glyph button centres on the tile.
 */
export function InfoCardHead({
  part,
  id,
  title,
  description,
  under,
  actions,
}: {
  part: InfoSectionKey;
  /** The heading's id, which the card's `aria-labelledby` names. */
  id: string;
  title: string;
  description: ReactNode;
  under?: ReactNode;
  actions?: ReactNode;
}) {
  const { Icon } = INFO_SECTIONS.find((section) => section.key === part)!;
  return (
    <div className="flex items-start gap-3">
      <span aria-hidden="true" className={GLYPH_TILE}>
        <Icon className="text-ink-meta size-5" />
      </span>
      <div className="min-w-0 flex-1">
        <SectionHeading id={id}>{title}</SectionHeading>
        <p className="text-body text-ink-meta mt-0.5">{description}</p>
        {under}
      </div>
      {actions && <div className="flex h-10 shrink-0 items-center gap-4">{actions}</div>}
    </div>
  );
}
