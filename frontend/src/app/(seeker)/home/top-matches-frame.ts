/**
 * Top Matches' list frame, shared by its rows (./top-matches-list.tsx)
 * and its skeleton (./top-matches.tsx). A plain module, since a server
 * component cannot read a value out of a "use client" file.
 *
 * THE LIST NEVER SCROLLS INSIDE THE PAGE (KAN-828): it shows the first
 * `SHOWN` rows at every width, and See More, under a rule across the
 * tile's foot, shows the rest in place. From @4xl/main it scrolled inside
 * its tile at `h-scroll-box`, so with the pointer over it the mouse wheel
 * moved the list and not the page, and a swipe that reached its end was
 * trapped; below @4xl/main it already showed five rows and let the page
 * scroll.
 */
export const LIST = "mt-4 flex flex-col gap-2";

/** How many rows show before See More. */
export const SHOWN = 5;
