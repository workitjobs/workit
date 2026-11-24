import { readEvents } from "@/components/scout/stream";
import type { GenerateStreamEvent } from "@/lib/built-resume-actions";
import { markResumesStale } from "@/lib/resumes-stale";

/**
 * "No, build one for me" (2026-11-17): a resume started from scratch, at
 * once, Generate's `blank` (2026-11-18): the header alone, every saved entry
 * and skill hidden on it, and no duplicate check. Onboarding then opens it
 * in the real editor, whose tour walks the student through adding their
 * school, jobs, projects and skills (resumes/[resumeId]/walkthrough.tsx).
 * Generated from the whole bank, a returning student's came out full, or
 * opened the resume they already had, so the tour had nothing to add. Three
 * builder pages asked for those first, beside a sketch that wrote them in a
 * resume's shape, which students took for the real resume.
 */
export async function makeResume(): Promise<{
  name: string | null;
  id: string | null;
  error: string | null;
}> {
  const res = await fetch("/api/resume-generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blank: true }),
  });
  if (!res.ok || !res.body) {
    const body: unknown = await res.json().catch(() => null);
    const detail = (body as { detail?: unknown } | null)?.detail;
    return {
      name: null,
      id: null,
      error: typeof detail === "string" ? detail : "WorkIt couldn't make your resume. Try again.",
    };
  }
  for await (const event of readEvents<GenerateStreamEvent>(res.body)) {
    if (event.type === "done") {
      markResumesStale();
      return { name: event.resume.name, id: event.resume.id, error: null };
    }
    if (event.type === "error") return { name: null, id: null, error: event.message };
  }
  return { name: null, id: null, error: "WorkIt stopped before your resume was ready. Try again." };
}
