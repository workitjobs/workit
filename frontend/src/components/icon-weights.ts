/**
 * The Phosphor weights the bundle keeps, beyond regular (KAN-782).
 *
 * Each Phosphor glyph ships all six of its weights in one table, and
 * Turbopack copies a glyph into the server chunk of every route that draws
 * it. So the Worker carried light and thin, which nothing draws, and bold,
 * fill and duotone for glyphs that never use them. A loader
 * (`scripts/phosphor-weights-loader.cjs`, set in `next.config.ts`) cuts each
 * glyph's table to regular plus the weights named for it here, on the server
 * and in the browser alike.
 *
 * A glyph drawn at a weight missing here draws nothing. `icon-weights.test.ts`
 * reads every `weight=` in `src/` and fails until the glyph is listed, and
 * fails on a listed glyph that no longer draws at that weight. Names are
 * Phosphor's, without the `Icon` suffix (`CaretLeft` for `CaretLeftIcon`).
 */
export const ICON_WEIGHTS = {
  bold: [
    "ArrowsDownUp",
    "CaretLeft",
    "Check",
    "DotsSixVertical",
    "Minus",
    "PencilSimple",
    "Plus",
    "Warning",
    "X",
  ],
  fill: ["BookmarkSimple", "Cursor", "CursorClick", "Pause", "Play", "Star"],
  duotone: [
    "Briefcase",
    "Certificate",
    "GraduationCap",
    "ListBullets",
    "RocketLaunch",
    "Scissors",
    "Stack",
    "Trophy",
    "UsersThree",
    "Wrench",
  ],
} satisfies Record<"bold" | "fill" | "duotone", string[]>;
