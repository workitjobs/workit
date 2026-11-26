"use client";

import { useTailoredIds } from "../list-data";

/**
 * The Tailor button's words: "Tailored Resume" once the student has one for
 * this job posting. A job's own page reads its built resumes (`tailored`,
 * ./job-view.tsx); the split view's open job on /jobs skips that read and
 * looks the job up in the tailored ids /jobs read once (../list-data.tsx,
 * KAN-916).
 */
export function TailorLabel({ jobId, tailored }: { jobId: string; tailored: boolean }) {
  const ids = useTailoredIds();
  return tailored || ids?.includes(jobId) ? "Tailored Resume" : "Tailor My Resume";
}
