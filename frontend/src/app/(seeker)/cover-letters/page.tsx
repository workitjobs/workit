import { CloudSlashIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import { connection } from "next/server";

import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";
import { listCoverLetters } from "@/lib/cover-letter-actions";

import { SEEKER_GUTTER } from "../gutter";
import { ResumesHeader } from "../resumes/header";
import { CoverLetters } from "./cover-letters";

export const metadata: Metadata = {
  title: "Cover Letters",
  description: "The cover letters WorkIt writes for your applications.",
};

/**
 * /cover-letters, Documents' second tab (KAN-766), beside Resumes: every
 * cover letter WorkIt wrote, as written answers on the applications whose
 * forms asked for one (`GET /applicants/{id}/cover-letters`, step 1 of
 * `docs/cover_letters.md`), in ./cover-letters.tsx. Uploads, the letter
 * each application sent and writing one in WorkIt are the design's later
 * steps. Live from the API; when it fails the page says so and offers a
 * retry, under the same tabs.
 */
export default async function CoverLettersPage() {
  await connection();
  const { letters, error } = await listCoverLetters();

  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      {letters ? (
        <CoverLetters letters={letters} />
      ) : (
        <>
          <ResumesHeader view="cover-letters" />
          <EmptyState
            Icon={CloudSlashIcon}
            title="Your Cover Letters Aren't Loading Right Now"
            className="mt-4"
            action={
              // A plain link, not <Link>: a full reload is what re-runs the fetch.
              // eslint-disable-next-line @next/next/no-html-link-for-pages
              <a
                href="/cover-letters"
                className={buttonClasses({ variant: "secondary", size: "sm" })}
              >
                Try Again
              </a>
            }
            detail={process.env.NODE_ENV === "development" ? error : undefined}
          >
            We couldn&apos;t reach your cover letters. Try again in a few minutes.
          </EmptyState>
        </>
      )}
    </div>
  );
}
