import type { CookieOptions } from "@supabase/ssr";

/**
 * Seven days, counted from the last refresh. @supabase/ssr rewrites the
 * cookie each time the hour-long access token is refreshed, so this is an
 * idle limit: a week without a visit signs you out, regular use never does.
 */
const SESSION_MAX_AGE = 7 * 24 * 60 * 60;

/** The session cookie's name, chunked as `.0`, `.1` when large. */
export const SESSION_COOKIE = /^sb-.+-auth-token(\.\d+)?$/;

/**
 * The signed-in hint (KAN-743): a cookie page scripts may read, holding
 * only "1", never a token. The marketing pages are prerendered and the
 * session cookies are httpOnly, so without it the header could learn of a
 * session only from GET /api/session after the page loaded, and a signed-in
 * student saw Log in first. app/layout.tsx reads it before the first paint.
 */
export const SIGNED_IN_HINT = "workit-signed-in";

type CookieWrite = { name: string; value: string; options: CookieOptions };

/**
 * The options every sb-* cookie is written with. Every place that writes
 * them passes each cookie through this, by way of sessionCookieWrites().
 *
 * httpOnly: nothing in the browser reads the session. Every Supabase call
 * runs on the server, so page scripts have no reason to see the tokens, and
 * an XSS bug can't steal them. A createBrowserClient() would need this off.
 *
 * maxAge is set here, not through createServerClient's `cookieOptions`:
 * @supabase/ssr 0.12 ignores that maxAge and writes its 400-day default.
 * A maxAge of 0 is a deletion (sign-out, a stale chunk) and is left alone.
 */
export function sessionCookieOptions(options: CookieOptions): CookieOptions {
  return {
    ...options,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    maxAge: options.maxAge === 0 ? 0 : SESSION_MAX_AGE,
  };
}

/**
 * A batch of Supabase's cookie writes as they go to the browser: each
 * through sessionCookieOptions, then the signed-in hint to match. A batch
 * that writes a live session cookie sets the hint, with the session's idle
 * age so the two expire together; one that only deletes them clears it; one
 * that touches no session cookie leaves it alone.
 */
export function sessionCookieWrites(cookiesToSet: CookieWrite[]): CookieWrite[] {
  const writes = cookiesToSet.map(({ name, value, options }) => ({
    name,
    value,
    options: sessionCookieOptions(options),
  }));
  const session = writes.filter((write) => SESSION_COOKIE.test(write.name));
  if (session.length === 0) return writes;
  const live = session.some((write) => write.value !== "" && write.options.maxAge !== 0);
  return [...writes, signedInHint(live)];
}

/** The signed-in hint's write: set to "1", or deleted. */
export function signedInHint(signedIn: boolean): CookieWrite {
  return {
    name: SIGNED_IN_HINT,
    value: signedIn ? "1" : "",
    options: {
      path: "/",
      sameSite: "lax",
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      maxAge: signedIn ? SESSION_MAX_AGE : 0,
    },
  };
}
