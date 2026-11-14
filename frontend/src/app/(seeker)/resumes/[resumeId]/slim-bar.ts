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
