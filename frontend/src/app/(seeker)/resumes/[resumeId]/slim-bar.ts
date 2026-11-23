import { cn } from "@/lib/cn";

/** Every button on a bar reads muted, but for its real actions
 *  (`data-bar-action`), which keep their own colour: a filled button's words
 *  would be grey on purple. The phone editor's row and its line sheet
 *  (./phone.tsx) take it too, so a tool looks the same on both layouts
 *  (KAN-799): the phone's ghost glyphs were the brand's purple. */
export const BAR_BUTTONS =
  "[&_button:not([aria-pressed=true]):not([data-bar-action])]:text-ink-muted [&_button:not([aria-pressed=true]):not([data-bar-action]):hover]:text-ink";

/** A glyph button on the bar that stays pressed while its view is open (the
 *  side panel's button, the phone's zoom): the brand tint in the control's
 *  8px corner, as the bar's other buttons have. Ghost buttons take a 2px
 *  corner, meant for a focus ring around inline text, so the pressed fill
 *  read as a square block against the bar's round end (KAN-586). */
export const PRESSED_GLYPH = "rounded-control aria-pressed:bg-brand-tint aria-pressed:text-brand";

/** The slim bar's box: a quiet white row, not the brand-tinted bar, 44px
 *  with its 36px buttons, one row that never wraps (./bar-fold.tsx). The
 *  editor's toolbar (`Bar`, ./toolbar.tsx) on its own page and on Tailor's
 *  review, and an upload's page (../uploaded/[id]/viewer.tsx) all draw it, so
 *  like bars look alike (KAN-576); Tailor's was a pill of its own
 *  (`DOCS_BAR`) until KAN-799. */
export const SLIM_BAR = cn(
  "bg-panel/95 ring-border-subtle sticky top-2 z-20 flex min-h-11 flex-nowrap items-center gap-2 rounded-card px-2 py-1 ring-1 backdrop-blur",
  BAR_BUTTONS,
);

/**
 * The desk (2026-11-23, the user's pick of three): the toolbar and the
 * pages are one surface, as a Google Doc's are. The bar is the desk's top
 * row (`DESK_BAR`), with a hairline under it and no outline of its own,
 * and the pages lie on the desk's grey (`--color-well`) as paper, centred
 * at every zoom (`DESK_PAGES`). Until then the bar was a rounded white card
 * 8px over a square-cornered page on the near-white ground: two shapes
 * with a gap too small to part them and too large to join them, edges that
 * met only at 125%, an 8px strip of the page showing over the bar once it
 * stuck (`top-2`), and white paper on a ground one shade off white.
 * Editing, Tailor's review and an upload's page all draw it. The phone
 * keeps `SLIM_BAR`: its page fills the screen, with no desk to stand on.
 */
// `overflow-clip`, not `hidden`: it rounds the bar's corners at rest and
// makes no scroll box, so the bar still sticks, square once the desk's top
// has scrolled away; a rounded bar of its own left notches beside the
// desk's straight edges as it stuck
export const DESK = "bg-well ring-border-surface rounded-card flex flex-col overflow-clip ring-1";

/** The desk's top row: the slim bar, opaque, sticking at the very top, so
 *  nothing scrolls into view over it. */
export const DESK_BAR = cn(
  "bg-panel border-border-subtle sticky top-0 z-20 flex min-h-11 flex-nowrap items-center gap-2 border-b px-2 py-1",
  BAR_BUTTONS,
);

/** Room around the paper on the desk, wider where the column is wide. */
export const DESK_PAGES = "px-3 py-4 @2xl/main:px-6 @2xl/main:py-6";
