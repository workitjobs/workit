import {
  ListBulletsIcon,
  RowsIcon,
  SidebarSimpleIcon,
  SquaresFourIcon,
} from "@phosphor-icons/react/ssr";

/**
 * The app's layouts, each with one name and one glyph wherever a view
 * switch offers it (2026-11-11, the user's rule: the same view is never
 * drawn under two names or two icons). Every view switch builds its options
 * here (`viewOption`): the Jobs page (jobs/view-switch.tsx), the Tracker
 * (applications/view-switcher.tsx) and Documents (resumes/built-resumes.tsx).
 *
 *   List View    rows, one item a line: the Tracker's table (Table View,
 *                with a table glyph, until 2026-11-11), Documents' table,
 *                and the Jobs page's list where it has no room for a split
 *   Card View    wide cards, one a row: the Jobs feed ("Cards View" until
 *                2026-11-11) and the Tracker's cards
 *   Grid View    small cards, several a row: Documents' first pages
 *   Split View   a list beside the open item: the Jobs page only
 *
 * A new view takes one of these when it is the same layout, whatever its
 * page calls its items; a layout none of them is joins this list first.
 * The Calendar's Month, Week and Agenda are date ranges, not layouts, and
 * say so in words.
 */
export const VIEWS = {
  list: { label: "List View", Icon: ListBulletsIcon },
  cards: { label: "Card View", Icon: RowsIcon },
  grid: { label: "Grid View", Icon: SquaresFourIcon },
  split: { label: "Split View", Icon: SidebarSimpleIcon },
} as const;

export type ViewKind = keyof typeof VIEWS;

/** A segmented control's option for `kind`, under the page's own URL or
 *  stored `value` (the Tracker's table is still `?view=list`, its cards
 *  `?view=grid`). */
export function viewOption<V extends string>(kind: ViewKind, value: V) {
  const { label, Icon } = VIEWS[kind];
  return { value, label, icon: <Icon aria-hidden className="size-4" /> };
}
