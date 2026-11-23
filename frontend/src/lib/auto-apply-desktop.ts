/**
 * WorkIt Auto Apply, the Mac app (KAN-723), as the website offers it
 * (KAN-922).
 *
 * Where `WorkIt Auto Apply.dmg` downloads from, or null while there is no
 * build to download. W8 of docs/desktop_application_auto_apply.md makes the
 * signed, notarized DMG and puts it on Cloudflare R2; set its address here
 * then, and nothing else.
 *
 * While it is null, nothing offers a file that does not exist: the home
 * hero's Download for Mac, the Auto Apply page's Mac answer, the app's top
 * bar button and the Auto Apply queue's offer stay hidden, and the public
 * `/download` page and the header's Download link, which stay public (the
 * user's call, 2026-11-19), say Coming soon in place of the download. The beta's
 * daily model limit is not guarded here: a public link lets anyone
 * download, so a limit on who may use the app belongs at its sign-in.
 */
export const DESKTOP_DOWNLOAD_URL: string | null = null;

/** The public page that offers the app (app/(landing)/download/). */
export const DESKTOP_PAGE = "/download";

/** What the app needs (D17, D18 and W8 of the design doc) and its price
 *  (D6: a free beta with a daily Usage cap), for both pages that list it. */
export const DESKTOP_NEEDS = {
  mac: "Apple Silicon Mac (M1 and later), macOS 13 or later",
  chrome: "Google Chrome",
  price: "Free during the beta, with a daily usage limit",
} as const;
