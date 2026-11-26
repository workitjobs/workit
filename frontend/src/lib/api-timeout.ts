/**
 * How long the app waits for one read from the API (2026-11-24): 10
 * seconds, then the read fails as if the API were down, so the page shows
 * its failed state (`LoadFailed`, "Try Again") or leaves the part out.
 *
 * WHY. Until then no call to the API had a limit. On 2026-11-24 the shared
 * database was overloaded (a Supabase dashboard report ran 25 minutes on
 * the Nano compute while the scrape imported), each read took 10 to 30
 * seconds or never answered, and every signed-in page waited on them:
 * Open WorkIt and the Jobs page showed nothing at all for over 30 seconds,
 * with no error and no way on.
 *
 * READS ONLY (a GET, or `init` with no method). A write is never cut off:
 * Tailor, Generate, Scout and an upload run for longer than any read, and
 * a write the app gave up on can still finish on the server, so the page
 * would say it failed when it had not.
 *
 * A caller's own signal is kept: the read stops at whichever comes first.
 * The limit covers the whole read, the body included, so a read whose
 * answer is still arriving at 10 seconds fails too.
 */
export const READ_TIMEOUT_MS = 10_000;

/** `init`, with the read limit added when it is a read. */
export function withReadTimeout(init: RequestInit = {}, ms = READ_TIMEOUT_MS): RequestInit {
  const method = (init.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") return init;
  const limit = AbortSignal.timeout(ms);
  return { ...init, signal: init.signal ? AbortSignal.any([init.signal, limit]) : limit };
}
