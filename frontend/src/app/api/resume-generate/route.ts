import { encodeId } from "@/lib/applicant-call";
import { apiFetch } from "@/lib/auth";
import { getApplicantSession } from "@/lib/session";

/**
 * The browser's door to a streamed Generate (KAN-444), the same shape as
 * /api/tailor: a route handler because the reply is an NDJSON stream of
 * Generate's steps (`lib/built-resume-actions.ts`, `GenerateStreamEvent`).
 * It adds the session's token and the applicant's path and pipes the API's
 * lines back untouched; the API checks the account owns the path and
 * decides the rest. A route handler's write never clears the router's
 * copies, so the page marks the resume lists stale itself
 * (`lib/resumes-stale.ts`).
 */
export async function POST(request: Request) {
  let session: { id: string; token: string };
  try {
    session = await getApplicantSession();
  } catch {
    return Response.json({ detail: "Sign in to generate a resume." }, { status: 401 });
  }

  try {
    const upstream = await apiFetch(
      `/applicants/${encodeId(session.id)}/built-resumes/stream`,
      { method: "POST", body: await request.text() },
      session.token,
    );
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { detail: "WorkIt can't reach its server right now. Try again in a minute." },
      { status: 502 },
    );
  }
}
