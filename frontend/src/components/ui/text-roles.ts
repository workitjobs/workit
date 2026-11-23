/**
 * Text roles (KAN-927): the style of each kind of text that several screens
 * draw by hand, named once. A screen imports the role (`TEXT.tableCell`) and
 * never copies its classes, so a size change moves one line here. Every
 * table had copied its header and cell classes into its own file, six
 * copies in all, and the type inventory of 2026-11-20 found them drifting.
 *
 * Only text drawn by hand lives here. A role that a `ui/` part owns (a
 * button's label, a field's label, a section heading) stays in that part.
 * `/design-kit/type` draws each role with its size, line height, weight and
 * colour read from the stylesheet, and flags a role whose value differs
 * from docs/design.md's Legibility table (Still open lists the same).
 *
 * The value is the role's type token and colour only. Spacing, truncation
 * and layout stay with the call site: `cn("px-4", TEXT.tableCell)`.
 */
export const TEXT = {
  /** A table's column heading: Job, Location, Applied. */
  columnHeader: "text-note text-ink-meta font-medium",
  /** A fact in a table's row: a place, a date, a count. design.md's table
   *  says 14px (`text-body`); every seeker table draws 12px today. */
  tableCell: "text-note text-ink",
  /** A table row's name, when it names a job. A resume's or a letter's row
   *  draws 450 today. */
  rowTitle: "text-label text-ink font-semibold",
  /** One line under a name: the employer, the place. */
  secondaryLine: "text-note text-ink-meta",
  /** A sentence under a field that says what goes in it. */
  hint: "text-note text-ink-meta",
  /** A sentence under a field, a button or a form that says what went
   *  wrong (design.md, "An error shows where the student acted"). */
  error: "text-note text-danger",
  /** Body copy: a dialog's text, a message, an answer. */
  body: "text-body text-ink",
  /** Long reading: a job's description and requirements. Tailwind's stock
   *  16px, since the scale has no 16px reading token yet. */
  longReading: "text-base text-ink",
  /** A date or a count beside other text. Never a sentence. */
  meta: "text-meta text-ink-meta",
} as const;

export type TextRole = keyof typeof TEXT;
