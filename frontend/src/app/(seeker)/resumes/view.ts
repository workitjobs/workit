/**
 * The Resumes tab's two layouts (KAN-766): the table after the Tracker's,
 * or the grid of first pages, after Google Drive's and Simplify's. The choice is a
 * cookie, so the server draws the chosen layout with no flash of the other,
 * as the Jobs page's view is (../jobs/view.ts). Its own module because the
 * action, the server's read and the switch all need these.
 */
export type ResumesLayout = "list" | "grid";

export const RESUMES_LAYOUT_COOKIE = "workit-resumes-layout";
