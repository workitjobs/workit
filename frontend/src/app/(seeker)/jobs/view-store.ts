import { useSyncExternalStore } from "react";

import { JOBS_VIEW_COOKIE, JOBS_VIEW_MAX_AGE, type JobsView } from "./view";

/**
 * The view the Jobs page shows, held in the browser (KAN-916). The server
 * draws a hard load in the cookie's view (./view), and every part that
 * differs between the views reads it here, starting from the view the server
 * drew (`drawn`), so hydration matches and nothing flashes.
 *
 * A SWITCH CHANGES IT HERE AND WRITES THE COOKIE, AND ASKS THE SERVER FOR
 * NOTHING. The switch used to set the cookie in a server action, and an action
 * that sets a cookie draws the whole page again in its answer: the shell's
 * reads, the layout's and the page's, Best Match scored again included (0.9 s
 * to 3 s locally, more with Best Match and no filters). Now each view draws
 * from the list already on screen, and the cookie only tells the next server
 * draw which view to start in.
 *
 * Kept for the tab, so a Back to the Jobs page, or /search, shows the view
 * last picked even where the server drew the other one from an older cookie
 * (another tab's choice).
 */
let chosen: JobsView | null = null;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The view to draw: the one picked in this tab, else the one the server drew. */
export function useJobsView(drawn: JobsView): JobsView {
  return useSyncExternalStore(
    subscribe,
    () => chosen ?? drawn,
    () => drawn,
  );
}

/** Shows `view` at once and keeps it for the next visit. */
export function chooseJobsView(view: JobsView) {
  chosen = view;
  document.cookie = `${JOBS_VIEW_COOKIE}=${view}; path=/; max-age=${JOBS_VIEW_MAX_AGE}; samesite=lax`;
  for (const listener of listeners) listener();
}
