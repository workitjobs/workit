import type { CSSProperties, ReactNode, Ref } from "react";

import { cn } from "@/lib/cn";

/**
 * The landing pages' shared frame: the content width, the rounded panels
 * every full-width band sits in, and the section heading. The home page,
 * the feature pages, Pricing and the Resources pages all draw with these, so the pages read as
 * one site; add a shared piece here rather than copying it into a page.
 */

/** The header's links, Features ▾, Resources ▾ and Pricing: one box for
 *  all three, so their text lines up. A bare inline link sat 1px below the
 *  Features button, its 14px text on the baseline of the list item's 16px
 *  line. A hover tints the box, as in the menus' items: the slate-800 text
 *  darkening to ink was too slight to see. */
export const NAV_ITEM =
  "text-ink inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-slate-900/[0.04]";

/** The site's `container-page` utility. */
export const CONTAINER = "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8";

/**
 * A full-width band drawn as a rounded panel inset from the window's edges,
 * after Calendly: the inset on the outer element, the fill and corners on
 * the panel inside it. The footer uses the same inset and radii.
 *
 * Corners nest (KAN-923, the user's call): an outer corner is the inner
 * corner plus the padding between them, so the two curves run parallel. A
 * tile or a framed box is 16px (`rounded-2xl`); a card holding one 12px in
 * is 28px; the hero panel holds its 16px tiles 8px in on a phone and 12px
 * from sm, so a panel is 24px, then 28px. It was 32px, then 48px from lg,
 * which the user found too round beside the hero's tiles.
 */
export const PANEL_INSET = "px-2 sm:px-6";
export const PANEL = "rounded-[1.5rem] sm:rounded-[1.75rem]";

/**
 * How long the pinned tour's panel takes to turn into the hiring-systems
 * section's, in vh, from lg up with motion: the tour keeps that much pin after
 * its last stop, and the section starts pinned, unseen, for that stretch
 * (KAN-540). One number for both, or the tour unpins under the section or
 * the section leaves a gap.
 */
export const TOUR_COVER_VH = 100;

/**
 * The marketing pages' type scale (KAN-923, after Calendly's): each step
 * has one job, and the steps carry the hierarchy, not the weight, so every
 * heading is weight 500. Plus Jakarta Sans for the hero and each chapter
 * (h1 to h3 take it by landing.css's rule), Newsreader for a product's own
 * section (`product`, the home page's product sections and hiring systems),
 * Inter for the rest. Before it every h2 was Jakarta 600 at 30 to 36px, so
 * nothing read as a chapter and nothing as a detail, which the user named
 * as part of the site looking AI-made. Use these, not a size of your own.
 */
export const TYPE = {
  /** The hero's h1: 72px from lg, 40px on a phone. */
  display:
    "text-[2.5rem] leading-[1.05] font-medium tracking-[-0.035em] text-balance sm:text-6xl lg:text-[4.5rem]",
  /** A chapter's centred h2 (SectionHeading, the closing call to action):
   *  56px from lg, 34px on a phone. */
  chapter:
    "text-[2.125rem] leading-[1.08] font-medium tracking-[-0.03em] text-balance sm:text-5xl lg:text-[3.5rem]",
  /** A product's left-aligned h2, in the serif: 48px from lg, 30px on a
   *  phone. Newsreader runs smaller than Jakarta, so it takes a size up. */
  product:
    "font-editorial text-[1.875rem] leading-[1.1] font-medium tracking-[-0.015em] text-balance sm:text-[2.5rem] lg:text-5xl",
  /** A card's heading: 28px, 24px on a phone. */
  card: "text-2xl leading-tight font-medium tracking-[-0.015em] text-balance sm:text-[1.75rem]",
  /** A list item's title inside a section (an accordion row). */
  item: "text-lg leading-snug font-medium",
  /** The line under a display or chapter heading. */
  lead: "text-lg leading-[1.55] text-pretty sm:text-[19px]",
  /** A small line in capitals, set wide, in meta grey: the logo strip's
   *  line, a journey card's step. Never violet and never a label above a
   *  heading: the violet eyebrows over every section heading read as a
   *  template, and the user had them all removed (KAN-923). */
  eyebrow: "text-xs font-semibold tracking-[0.08em] uppercase",
} as const;

/** The pill above a hero's headline (a feature page's name, Pricing,
 *  a Resources page; the home hero has none since the user had its
 *  "For internships and new-grad roles" removed): frosted white, no border, one look on every
 *  page. Pricing's was violet glass in capitals. */
export const HERO_PILL =
  "text-ink inline-flex items-center gap-2 rounded-full bg-white/70 px-3.5 py-1.5 text-sm font-medium shadow-[var(--mk-shadow-float)] backdrop-blur-sm";

export function SectionHeading({
  id,
  title,
  subtitle,
  align = "center",
  className,
}: {
  /** The h2's id, for a section's aria-labelledby. */
  id?: string;
  title: string;
  subtitle?: string;
  align?: "center" | "left";
  className?: string;
}) {
  return (
    <div className={cn("max-w-3xl", align === "center" && "mx-auto text-center", className)}>
      <h2 id={id} className={cn(TYPE.chapter, "text-ink")}>
        {title}
      </h2>
      {subtitle && (
        <p className={cn(TYPE.lead, "text-ink-meta mx-auto mt-5 max-w-2xl")}>{subtitle}</p>
      )}
    </div>
  );
}

/**
 * A feature's ground for a `StudioBox` (KAN-923): a sky in the feature's own
 * colour, after Calendly's boxes. A pale wash at the top, near white
 * through the middle, where a bright band sits behind the scene's card like
 * a horizon, then the colour deepening to the foot, where it is the
 * feature's full colour, a step darker. One hue and one light, so the box
 * reads as a place the card sits in. It replaced blobs of the colour (and
 * of a second colour) over the tint: every blob sat at the same lightness,
 * with no light source and no direction, so the boxes read as flat and
 * muddy beside Calendly's (the user's comparison, 2026-11-19).
 *
 * No one text colour holds 4.5:1 on every foot (ink fails on the blue,
 * violet and pink; white on the green), so nothing writes straight on the
 * lower fifth of a box: text there sits on a card or a pill.
 */
export function studioGround({ glow }: { glow: string }) {
  const wash = (amount: number) => `color-mix(in oklab, ${glow} ${amount}%, white)`;
  const foot = `color-mix(in oklab, ${glow} 90%, var(--color-ink))`;
  return [
    `radial-gradient(70% 22% at 50% 46%, rgb(255 255 255 / 0.85), transparent 75%)`,
    `linear-gradient(180deg, ${wash(24)} 0%, ${wash(7)} 42%, ${wash(38)} 72%, ${foot} 100%)`,
  ].join(", ");
}

/**
 * The frame every moving or still picture on the home page sits in
 * (KAN-923): a box with the tiles' 16px corners on a feature's ground
 * (`studioGround`), with a fine grain (`.studio-box` in landing.css), so a
 * picture is a small object on the page and never the page itself. After
 * Calendly, whose animations all sit in boxes of 290 to 424px; the old
 * home page pinned whole screens to its scenes, which the user found
 * AI-made. Content sits above the texture.
 */
export function StudioBox({
  ground,
  className,
  style,
  ref,
  children,
}: {
  ground: string;
  className?: string;
  style?: CSSProperties;
  ref?: Ref<HTMLDivElement>;
  children: ReactNode;
}) {
  return (
    <div
      ref={ref}
      className={cn("studio-box relative isolate overflow-hidden rounded-2xl", className)}
      style={{ background: ground, ...style }}
    >
      {children}
    </div>
  );
}

/**
 * "Coming soon" beside something the product does not do yet. The tracker
 * stores no employer replies, so the tour's Updates stop and the
 * applications route's Interview and Job Offers stops carry it: once the
 * "How it works" section went, which had carried it on its Hear back card,
 * the page showed replies as working.
 */
export function SoonChip({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "bg-surface text-ink-muted shrink-0 rounded-full px-2 py-0.5 text-[11px] leading-4 font-semibold ring-1 ring-slate-900/5",
        className,
      )}
    >
      Coming soon
    </span>
  );
}
