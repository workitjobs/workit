/**
 * The Resumes tab's two layouts (KAN-766): the table after the Tracker's,
 * or the grid of first pages, after Google Drive's and Simplify's. The
 * choice is a cookie, so the server draws the chosen layout with no flash
 * of the other, as the Jobs page's view is (../jobs/view.ts); the loading
 * frame reads it too ((list)/loading.tsx). Its own module, with no client
 * code, because the action, the server's reads and the switch all need
 * these: a constant a server file takes from a "use client" module arrives
 * as a client reference, not its value.
 */
export type ResumesLayout = "list" | "grid";

export const RESUMES_LAYOUT_COOKIE = "workit-resumes-layout";

/** The cookie's layout: the grid only when it says so. */
export function readResumesLayout(value: string | undefined): ResumesLayout {
  return value === "grid" ? "grid" : "list";
}

/** The grid's columns: two, then four from `@3xl` of the page's column. */
export const RESUME_GRID = "grid grid-cols-2 gap-4 @3xl:grid-cols-4";

/** A grid card's picture's shape: the top of the page, not all of it
 *  (`ResumeThumbnail`). */
export const THUMBNAIL_RATIO = "4 / 3";
