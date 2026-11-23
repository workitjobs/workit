import type { CSSProperties, ReactNode, Ref } from "react";

import { cn } from "@/lib/cn";

import { Arrive } from "./arrive";

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
 * (h1 to h3 take it by landing.css's rule) and for a product's own section
 * (`product`), Inter for the rest. A product's heading was Newsreader, a
 * serif, after Calendly's split; the only serif on the site, it read as
 * fancy and out of place beside every other heading (the user's call,
 * 2026-11-20), and the face went with it. Before it every h2 was Jakarta 600 at 30 to 36px, so
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
  /** A product's left-aligned h2: 44px on a wide laptop, 30px on a phone,
   *  a step under a chapter's 56px, in the same face. From lg it follows
   *  the window (3.4vw, 36 to 44px): at 1024px its column is 444px wide,
   *  and at a fixed 44px a 46-character headline ("The easiest way to make
   *  a resume for every job") took three lines there, where every product
   *  headline is held to two. */
  product:
    "text-[1.875rem] leading-[1.08] font-medium tracking-[-0.03em] text-balance sm:text-[2.5rem] lg:text-[clamp(2.25rem,3.4vw,2.75rem)]",
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
  // It rises as it arrives (`Arrive`, `.rise` in landing.css): the title
  // from behind its own foot, as the hero's headline, then the subtitle.
  // No fade. On every page that draws a section heading.
  return (
    <Arrive className={cn("max-w-3xl", align === "center" && "mx-auto text-center", className)}>
      <h2 id={id} className={cn(TYPE.chapter, "rise text-ink")}>
        {title}
      </h2>
      {subtitle && (
        <p
          className={cn(TYPE.lead, "rise text-ink-meta mx-auto mt-5 max-w-2xl")}
          style={{ "--rise": "0.12s" } as CSSProperties}
        >
          {subtitle}
        </p>
      )}
    </Arrive>
  );
}

/**
 * A box's four colours, by the feature colour it is asked for: the ground,
 * a neighbour hue for the lower left, a second neighbour for the upper
 * right, and a pale tone for the streak of light between them. Neighbours
 * on the colour wheel, a step either side of the feature's own colour, so
 * a box blends as one family and still reads as blue, peach, green or
 * pink at a glance. Written at full strength; `studioGround` mixes each
 * toward white (`STRENGTH`).
 */
export const MESH: Record<string, [ground: string, low: string, high: string, light: string]> = {
  // Resume Builder: blue, with cyan below and periwinkle above.
  "var(--color-advanced)": ["#3f8cf0", "#2fd6dc", "#8d86f4", "#a8d6f8"],
  // Job Matching: peach, with yellow below and coral above.
  "var(--color-matching)": ["#fb8f45", "#ffcc55", "#f76f8e", "#ffdcb8"],
  // Auto Apply: green, with lime below and teal above.
  "var(--color-positive)": ["#27bd84", "#a3e065", "#22b4cc", "#baf1d2"],
  // Application Tracker: pink, with coral below and plum above.
  "var(--color-updates)": ["#d655b0", "#ff9274", "#9a6ff2", "#f8c8e8"],
  // WorkIt itself: violet, with blue below and magenta above.
  "var(--color-brand)": ["#7b58ec", "#4f93f6", "#c95fe2", "#cdbffa"],
};

/**
 * How much of each `MESH` colour a ground keeps; the rest is white. Pastel
 * (the user's pick, 2026-11-21, over the colours at full strength, seen
 * side by side in the page): the site is paper and ink, a white page with
 * hairlines, and four boxes at full strength in the hero were louder than
 * the headline over them. The blend between neighbours stays; only its
 * strength dropped.
 */
const STRENGTH = 46;

/**
 * A feature's ground for a `StudioBox`: a blend of neighbouring
 * colours (2026-11-21, after a reference the user gave: one image where
 * blue runs into cyan and periwinkle under a grain you can see). The
 * feature's colour fills the box; a neighbour hue pools in the lower left
 * and another in the upper right; a pale streak crosses between them, the
 * light.
 *
 * What it replaced, each the user's call: a sky in one colour, pale at the
 * top to half strength at the foot, which read as AI-made and odd ("just
 * blue and white"); the same sky ending in the full colour, too strong
 * with four boxes side by side; and, first, blobs of the colour over a
 * pale tint, flat and muddy. The lesson across the three: one colour and
 * white is not a gradient worth looking at; the interest is in the blend
 * between neighbours.
 *
 * Nothing writes straight on a box: text sits on a card or a pill
 * (`GroundNote`), so a scene reads the same whatever the ground's
 * strength. A colour with no entry in `MESH` gets the same shape from
 * mixes of itself.
 */
export function studioGround({ glow }: { glow: string }) {
  const mix = (amount: number, into: string) => `color-mix(in oklab, ${glow} ${amount}%, ${into})`;
  const [ground, low, high, light] = MESH[glow] ?? [
    mix(80, "white"),
    mix(55, "white"),
    mix(85, "var(--color-ink)"),
    mix(30, "white"),
  ];
  const tone = (color: string) => `color-mix(in oklab, ${color} ${STRENGTH}%, white)`;
  return [
    `radial-gradient(62% 58% at 84% -6%, ${tone(high)}, transparent 72%)`,
    `radial-gradient(78% 72% at -10% 70%, ${tone(low)}, transparent 68%)`,
    `radial-gradient(58% 40% at 34% 34%, ${tone(light)}, transparent 74%)`,
    tone(ground),
  ].join(", ");
}

/**
 * The frame every moving or still picture on the home page sits in
 * (KAN-923): a box with the tiles' 16px corners on a feature's ground
 * (`studioGround`), with no texture over it (a grain was removed, landing.css), so a
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
