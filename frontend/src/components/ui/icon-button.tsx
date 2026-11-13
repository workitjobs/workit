import type { ComponentProps, ReactNode } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/shadcn/tooltip";
import { cn } from "@/lib/cn";

/**
 * A button whose entire content is an icon, so it must be labelled in words.
 *
 * `label` is required rather than optional: an icon-only control with no
 * accessible name is unusable with a screen reader, and making the prop
 * mandatory is what stops one from shipping. Pass the icon as children and size
 * it there — the glyph sizes differ per usage even where the button does not.
 *
 * The label is also the tooltip, unless `tooltip` says otherwise. `false`
 * shows none, for a glyph read on sight (Close, Back, ⋯, Undo; the list is
 * in docs/design.md, Components, 2026-11-12), except on a `soon` button.
 * Pass a string when
 * the label names the thing the button acts on — "Save Staff Frontend
 * Engineer" — because that detail is for a screen reader, which reaches the
 * button without the card around it and would otherwise hear "Save" ten times
 * down the feed. A sighted user is hovering inside that card already, so the
 * tooltip says just "Save". The label stays on aria-label either way: Base
 * UI's tooltip is visual only and never becomes the button's accessible name.
 *
 * The trigger is the button itself — Base UI's Tooltip.Trigger renders a
 * <button> — rather than a wrapper around one, so there is no extra element in
 * the flex rows these sit in. TooltipProvider is in the root layout.
 */
/** The `glyph` variant's classes. An open menu keeps the hover look on its
 *  trigger (`data-popup-open`).
 *
 *  EVERY ICON BUTTON IS AN IconButton, a menu's or a popover's trigger too
 *  (`render={<IconButton …/>}` on the trigger), so each has one look and
 *  one tooltip rule (2026-11-11). These classes were exported for two
 *  triggers drawn without it, the job's ⋯ menu and Table Settings. */
const GLYPH_BUTTON =
  "text-ink hover:text-brand hover:bg-hover data-popup-open:bg-hover data-popup-open:text-brand focus-visible:ring-brand-ring -m-1.5 inline-flex items-center justify-center rounded-full p-1.5 [--hit-grow:2px] focus-visible:ring-2";

/**
 * WHERE A BARE GLYPH BUTTON SITS SETS ITS SIZE (2026-11-12): `place`, never a
 * size class at the call site. Both are Experiences' look, a 32px round
 * target with a grey disc under the pointer; only the glyph differs.
 *
 * - `heading`: a card's or a section's own action at its heading's end, with
 *   a 20px glyph, as LinkedIn's: Experiences' Add, Edit and ⋯, My Profile's
 *   and Application Info's cards (profile/section-action.tsx).
 * - `row`: everything else, with a 16px glyph: a row's actions (a resume's
 *   Rename, Download, Delete, ⋯), a panel's or a dialog's Close and Back, a
 *   card's Undo, a filter's Clear.
 *
 * Close was 24, 28, 32 and 36px, ⋯ came in four looks and Tailor's Undo in
 * three sizes in one panel, each call site picking its own class. Two
 * exceptions keep their own: the job card's Save and ⋯ (`glyph`, sized to
 * sit where a bare glyph did) and a chip's own small glyphs. The glyph's size
 * is set here, over any size class on the glyph itself.
 */
const PLACES = {
  heading: "hover:bg-hover size-8 rounded-full [&_svg]:size-5",
  row: "hover:bg-hover size-8 rounded-full [&_svg]:size-4",
} as const;

export type IconButtonPlace = keyof typeof PLACES;

/** The `soft` variant's classes. */
const SOFT_BUTTON =
  "border-border-surface bg-panel text-ink hover:bg-hover focus-visible:ring-brand-ring inline-flex items-center justify-center rounded-full border focus-visible:ring-2";

const VARIANTS = {
  /** Bare glyph: top-bar utilities and row actions. Centred in whatever box
   *  the call site sizes it to, and the hit area reaches 8px past the box,
   *  so an unsized 16px glyph is still a 32px target with a mouse (44px on
   *  touch) without moving anything around it. */
  quiet:
    "text-ink hover:text-brand focus-visible:ring-brand-ring inline-flex items-center justify-center rounded-xs [--hit-grow:8px] focus-visible:ring-2",
  /** A bare glyph among a card's or a panel's own actions (Save, Not
   *  Interested, Ask Scout; the ⋮ menu draws the same look, `GLYPH_BUTTON`):
   *  ink at rest and, under the pointer, brand on a 28px hover disc. The
   *  box is padded out by a negative margin, so the glyph sits where an
   *  unsized quiet one did, and the disc plus `--hit-grow` is the 32px
   *  target. Brand alone on a 16px glyph read as no hover at all
   *  (2026-11-10). */
  glyph: GLYPH_BUTTON,
  /** Bordered and square. No screen uses it since 2026-11-09, when every
   *  icon button among buttons went `soft`; kept for the design kit and a
   *  screen that needs a square edge. Size it at the call site (size-9, the
   *  `sm` button height). */
  outline:
    "border-border-surface bg-panel text-ink hover:bg-hover focus-visible:ring-brand-ring rounded-control inline-flex items-center justify-center border focus-visible:ring-2",
  /** A round icon button with a secondary Button's fill and edge (white,
   *  --color-border-surface, the hover fill), ONLY ON THE GREY PAGE GROUND
   *  (2026-11-09): the Jobs page's and the Tracker's Clear Filters and All
   *  Filters. On a white card, header or panel an icon button is `quiet`, a
   *  bare glyph (a card's Save and "⋯", Tailor's Undo All): a white circle
   *  on white only repeated the surface, the user's rule.
   *  It was a soft grey with no border for a day, which made it a second
   *  family beside the white buttons and sat close to the disabled fill
   *  (8% ink), so a live Save read as switched off. Size it at the call
   *  site. */
  soft: SOFT_BUTTON,
  /** A bare glyph on the inverted surface: a toast's close (ui/toast.tsx,
   *  KAN-217). On-inverse at 80%, full on hover; never on a light page. */
  inverse:
    "text-on-inverse/80 hover:text-on-inverse focus-visible:ring-on-inverse inline-flex items-center justify-center rounded-xs [--hit-grow:8px] focus-visible:ring-2",
  /** Brand disc — an edit affordance overlapping the thing it edits. The border
   *  matches the panel behind it so the disc reads as cut out of the surface. */
  brand:
    "bg-brand text-on-brand border-panel hover:bg-brand-hover focus-visible:ring-brand-ring inline-flex size-6.5 items-center justify-center rounded-full border-2 focus-visible:ring-2 focus-visible:ring-offset-2",
} as const;

export type IconButtonVariant = keyof typeof VARIANTS;

type IconButtonProps = {
  label: string;
  /** Shown on hover in place of `label`, for a label too specific to read
   *  well. `false` shows none, for a glyph everyone reads on sight (below). */
  tooltip?: string | false;
  variant?: IconButtonVariant;
  /** Where it sits, which sets its size (`PLACES`): pass it on every bare
   *  glyph button, `quiet` or `inverse`; the others are sized by their own
   *  row (`soft`, `outline`, `brand`). */
  place?: IconButtonPlace;
  /** Not built yet (KAN-569): the button stays in its place, faded, does
   *  nothing, and says "Coming Soon" in its tooltip and its name. Unlike
   *  `disabled` it still takes the pointer and focus, since a disabled button
   *  shows no tooltip and so could not say why. */
  soon?: boolean;
  className?: string;
  children: ReactNode;
} & Omit<ComponentProps<"button">, "className" | "children" | "aria-label">;

export function IconButton({
  label,
  tooltip = label,
  variant = "quiet",
  place,
  soon = false,
  className,
  type = "button",
  disabled,
  onClick,
  children,
  ...props
}: IconButtonProps) {
  const buttonProps = {
    type,
    "aria-label": soon ? `${label}, coming soon` : label,
    "aria-disabled": soon || undefined,
    onClick: soon ? undefined : onClick,
    className: cn(
      // Every variant's target is 24px or more, 44px on touch (the
      // hit-area utility in globals.css, KAN-557).
      "hit-area relative",
      VARIANTS[variant],
      place && PLACES[place],
      // Presses in further than a button (90%): a glyph is small, and a
      // smaller squeeze would not read. Colours fade on the same clock.
      "transition-[color,background-color,border-color,transform] duration-150 ease-out focus-visible:outline-none active:scale-90 disabled:pointer-events-none disabled:opacity-50",
      className,
      // After the call site's classes, so no hover or press state outlives it.
      soon && "text-ink-subtle hover:text-ink-subtle cursor-default active:scale-100",
      soon && variant === "outline" && "hover:bg-panel",
    ),
    ...props,
  };

  // A "Coming Soon" button keeps its tooltip whatever the call site says: it
  // is the only thing that tells why the button does nothing.
  const tip = soon ? `${tooltip || label}: Coming Soon` : tooltip;
  if (tip === false) {
    return (
      <button disabled={disabled} {...buttonProps}>
        {children}
      </button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        // `disabled` on the trigger only stops the tooltip: the button itself
        // takes it through `render`, or a disabled button still clicks.
        render={<button disabled={disabled} />}
        disabled={disabled}
        {...buttonProps}
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{tip}</TooltipContent>
    </Tooltip>
  );
}
