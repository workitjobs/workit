/**
 * The look My Profile's and Application Info's cards share (Contact & Links,
 * the question cards, Application Answers), in one place so they cannot drift.
 *
 * Each card is a white `Card` on the grey ground (KAN-550), drawn with
 * `padding="none"` and SECTION_CARD: 20px of padding, 24px where the page is
 * wide, and room above it for a jump to its `section-<id>` address. They were
 * open sections split by hairlines until then, which on the grey ground read
 * as a long form with nothing to hold it.
 *
 * A FACT READS ITS VALUE FIRST (2026-11-11): its name small and grey
 * (FACT_LABEL), its value in ink at body size under it (FACT_VALUE), and a
 * missing value a faint dash (components/ui/missing.tsx). Each name was a
 * 16px semibold heading with a 20px glyph, as large as the card's own
 * title, with the value smaller and greyer under it, so the card read as a
 * list of headings and the answers as captions; 14 glyphs on Application
 * Info named what the labels already said. Editing, a field's label is a
 * form label over its control (FIELD_LABEL). Two columns where the card is
 * wide, one on a phone.
 */
export const SECTION_CARD = "scroll-mt-6 p-5 @xl/main:p-6";
export const FIELD_GRID = "mt-5 grid gap-x-10 gap-y-5 @xl/main:grid-cols-2";
/** A fact's name, over its value. */
export const FACT_LABEL = "text-note text-ink-meta";
/** A fact's value, the line the student reads. */
export const FACT_VALUE = "text-body text-ink mt-0.5 min-w-0";
/** A field's label while editing, over its control. */
export const FIELD_LABEL = "text-label text-ink block font-medium";
/** A group of facts' name (Application Answers' Availability, Address). */
export const GROUP_HEADING = "text-label text-ink font-semibold";
