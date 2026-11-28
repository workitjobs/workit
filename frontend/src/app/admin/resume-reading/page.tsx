import type { Metadata } from "next";

import { getResumeReading } from "@/lib/fill-report-queries";
import { windowOf } from "@/lib/scrape-status";

import { refuse } from "../refuse";
import { ReadingView } from "./view";

export const metadata: Metadata = { title: "Resume Reading" };

/**
 * Resume reading for admins (KAN-953): who read each uploaded resume, the
 * model or the rule-based parser, from the reading log (KAN-898). It answers
 * one question first, whether models are reading resumes
 * (lib/resume-reading.ts's `statusOf`), then gives the detail in one scroll
 * (./view.tsx).
 *
 * The period in the title row sets the days all of it shows, held in the
 * address. Each period is one read of the API, since a median cannot be cut
 * from a longer period's answer as Scrape Health cuts its days. Only
 * WorkIt's admins (the API's WORKIT_ADMINS) see it; anyone else gets the
 * 404, as /admin/fill-health.
 */
export default async function ResumeReadingPage({
  searchParams,
}: PageProps<"/admin/resume-reading">) {
  const window = windowOf(await searchParams);
  const { data, status } = await getResumeReading(window.days);
  if (!data) refuse(status);
  return <ReadingView health={data} window={window} />;
}
