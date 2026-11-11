"use server";

import { apiGet } from "@/lib/api";
import { extractErrorMessage } from "@/lib/auth";
import { getApplicantSession } from "@/lib/session";

/** Where an application stands (`job_applications.stage`). */
export type ApplicationStage =
  "saved" | "queued" | "needs_you" | "skipped" | "applied" | "interviewing" | "offer" | "rejected";

/**
 * A cover letter WorkIt wrote (KAN-766, `GET /applicants/{id}/cover-letters`):
 * a saved written answer whose Question type is `cover-letter`, with its
 * job posting and its application's stage. `job_id` and `name` are the
 * answer's key; `closed` when the Jobs page no longer lists the posting.
 */
export type CoverLetter = {
  job_id: string;
  name: string;
  label: string;
  text: string;
  own: boolean;
  answered_at: string | null;
  company: string | null;
  title: string | null;
  logo_url: string | null;
  company_domain: string | null;
  closed: boolean;
  stage: ApplicationStage;
};

export async function listCoverLetters(): Promise<{
  letters: CoverLetter[] | null;
  error: string | null;
}> {
  try {
    const { id, token } = await getApplicantSession();
    const res = await apiGet(`/applicants/${id}/cover-letters`, token);
    if (!res.ok) return { letters: null, error: await extractErrorMessage(res) };
    return { letters: (await res.json()) as CoverLetter[], error: null };
  } catch {
    return { letters: null, error: "Could not reach the server." };
  }
}
