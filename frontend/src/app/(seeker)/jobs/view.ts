/**
 * The Jobs page's two views (KAN-519): the large cards, or the split view, a
 * list of compact cards beside the open job. The choice is a cookie, so the
 * server draws the chosen view with no flash of the other; it stays with the
 * browser, as Key Requirements' folded state does. Its own module because the
 * server's read, the browser's store (./view-store) and the switch all need
 * these.
 */
export type JobsView = "cards" | "split";

export const JOBS_VIEW_COOKIE = "workit-jobs-view";

/** How long the choice is kept: a year, renewed by every switch. */
export const JOBS_VIEW_MAX_AGE = 60 * 60 * 24 * 365;

/** A cookie value as a view: anything but "split" is the cards. */
export function readJobsView(value: string | undefined | null): JobsView {
  return value === "split" ? "split" : "cards";
}
