import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE, SIGNED_IN_HINT, signedInHint } from "@/lib/supabase/cookies";

/**
 * GET /api/session: whether this browser holds a session cookie, for the
 * marketing header's "Open WorkIt" swap (KAN-581, `(landing)/session-swap.tsx`).
 * The marketing pages are static and the sb-* cookies are httpOnly, so the
 * page cannot read them itself; it asks here after it loads.
 *
 * It checks only that an sb-*-auth-token cookie exists (chunked as `.0`,
 * `.1` when large), never its value: no Supabase call, no token in the
 * answer. src/middleware.ts runs first and clears a cookie it cannot refresh, so a
 * dead session answers false. A forged cookie gets an "Open WorkIt" link that
 * /go-home sends on to sign in.
 *
 * It also writes the signed-in hint to match its answer (KAN-743,
 * lib/supabase/cookies.ts), so a session from before the hint existed, or a
 * hint left behind, is right on the next page load.
 */
export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const signedIn = request.cookies
    .getAll()
    .some((cookie) => SESSION_COOKIE.test(cookie.name) && cookie.value !== "");
  const response = NextResponse.json(
    { signed_in: signedIn },
    { headers: { "Cache-Control": "no-store" } },
  );
  const hinted = request.cookies.get(SIGNED_IN_HINT)?.value === "1";
  if (signedIn || hinted) {
    const { name, value, options } = signedInHint(signedIn);
    response.cookies.set(name, value, options);
  }
  return response;
}
