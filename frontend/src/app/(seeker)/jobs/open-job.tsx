"use server";

import { JobPage } from "./[jobId]/job-page";
import type { JobMatch } from "./[jobId]/job-view";
import type { Highlight } from "./data";

/**
 * The split view's open job, drawn for a switch from the Card View
 * (./list-views.tsx, KAN-916): the server drew the cards, the list is on
 * screen, and only the list's first job is missing beside it. The answer is
 * the job's page as the split view draws it, streamed; the page is not drawn
 * again, which a cookie set in an action would have done.
 *
 * `match` is the list row's score, so the job is not scored again. A public
 * entry point like every action: the job is read as the job's own page reads
 * it, with the session's token, and a forged score only changes what its own
 * sender sees, so it is checked for shape alone.
 */
export async function openJob(jobId: string, match: JobMatch) {
  return <JobPage jobId={String(jobId)} listed fromList={{ match: checked(match) }} />;
}

function checked(match: JobMatch): JobMatch {
  if (match == null || typeof match.score !== "number" || !Number.isFinite(match.score)) {
    return null;
  }
  const highlights = Array.isArray(match.highlights) ? match.highlights.slice(0, 3) : [];
  return {
    score: Math.max(0, Math.min(100, Math.round(match.score))),
    highlights: highlights.flatMap((h): Highlight[] =>
      h && typeof h.text === "string" && typeof h.met === "boolean"
        ? [{ text: h.text, detail: typeof h.detail === "string" ? h.detail : null, met: h.met }]
        : [],
    ),
  };
}
