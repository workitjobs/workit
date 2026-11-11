import { EnvelopeSimpleIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";

import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { ResumesHeader } from "../resumes/header";

export const metadata: Metadata = {
  title: "Cover Letters",
  description: "The cover letters WorkIt writes for your applications, and your own.",
};

/**
 * /cover-letters, Documents' second tab (KAN-766), beside Resumes. WorkIt
 * already writes cover letters, as written answers on the applications
 * whose forms ask for one (`written_answers`, question type
 * `cover-letter`), but no page lists them. What this tab holds is the
 * design in `docs/cover_letters.md`, for review before it is built; until
 * then it says what it will hold.
 */
export default function CoverLettersPage() {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <ResumesHeader view="cover-letters" />
      <EmptyState Icon={EnvelopeSimpleIcon} title="Cover Letters Are Coming" className="mt-4">
        Every cover letter WorkIt writes for your applications will be here, with the job it went
        to, and you will be able to upload your own.
      </EmptyState>
    </div>
  );
}
