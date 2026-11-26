import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";
import { SectionHeadingSkeleton } from "@/components/ui/section-heading";
import { getAutofillAnswers } from "@/lib/autofill-answers-actions";
import { getBank } from "@/lib/bank-actions";

import { FIELD_GRID } from "../../profile/field-styles";
import { INFO_CARD } from "./card-head";
import { InfoNav } from "./info-nav";
import { InfoPart, InfoParts } from "./info-part";
import { AnswerCards } from "./info-screen";
import { Transcript } from "./transcript";
import { InfoDiscardBar, InfoUnsaved } from "./unsaved";
import { WorkdaySignup } from "./workday-signup";
import { WritingSamples } from "./writing-samples";

export const metadata: Metadata = {
  title: "Application Info",
  description: "The answers and files WorkIt fills into your applications.",
};

/**
 * /auto-apply/info — Application Info (KAN-550): everything the extension
 * and the student's Claude fill into a form that is not on a resume. It all
 * sat on My Profile until KAN-550, which made that page a long form the
 * student scrolled past to find their own name and links: what an employer
 * sees stays there, and what only the autofiller reads moved here, under
 * the feature that uses it. It is Auto Apply's Application Info tab: the
 * frame and the tabs over the menu are ../layout.tsx's.
 *
 * IT WORKS AS SETTINGS DOES (2026-11-24, ./sections.ts says why): a menu
 * (./info-nav.tsx) beside one part at a time, each part at its own address
 * (`/auto-apply/info/<part>`), each card an open form with Save. **The
 * parts are drawn here, in the layout, all at once**, and stay mounted,
 * shown only while open (./info-part.tsx), so the menu switches them with no
 * read and an unsaved edit in one survives a look at another. The part's
 * page (./[section]/page.tsx) draws nothing: a layout stays mounted while
 * the part in the address changes, and a page would be drawn again, and
 * drop its forms' edits, on every refresh of a different part's address.
 *
 * Work Authorization, Voluntary Self-Identification (closed until Show)
 * and Application Answers read the answer bank here, on the server, with
 * the experience bank, whose education entries give Application Answers'
 * School Year (a failed bank read leaves School Year unknown, not the
 * page). They stream in their own boundary, so the menu and the files
 * never wait on them. Transcript (./transcript.tsx), Writing Samples
 * (./writing-samples.tsx) and Workday Sign-Up (./workday-signup.tsx, which
 * opens the extension's own page) read their own. A failed answers read
 * shows the failed read's card with Try Again (KAN-819), never a form of
 * "Not Answered" that would pass for the student's real answers.
 *
 * On a phone the menu is a row above the part.
 */
export default function ApplicationInfoLayout({ children }: { children: ReactNode }) {
  return (
    <InfoUnsaved>
      <div className="grid gap-6 sm:grid-cols-[13rem_minmax(0,1fr)] sm:gap-8">
        <InfoNav />
        {/* At most 48rem, design.md's settled form width (2026-11-11): at the
            page's full width a card's two columns of fields sat far apart and
            its description ran past 150 characters a line. */}
        <InfoParts>
          <Suspense fallback={<AnswersLoading />}>
            <Answers />
          </Suspense>
          <InfoPart name="files">
            <Transcript />
            <WritingSamples />
            <WorkdaySignup />
          </InfoPart>
          {/* The part's page: nothing, or the 404 of an unknown part. */}
          {children}
          <InfoDiscardBar />
        </InfoParts>
      </div>
    </InfoUnsaved>
  );
}

async function Answers() {
  const [answers, bank] = await Promise.all([getAutofillAnswers(), getBank()]);
  if (answers.error != null) {
    const failed = (
      <LoadFailed
        title="Your Answers Aren't Loading Right Now"
        detail={process.env.NODE_ENV === "development" ? answers.error : undefined}
      >
        We couldn&apos;t reach your application answers. Try again in a few minutes.
      </LoadFailed>
    );
    return (
      <>
        <InfoPart name="work-authorization">{failed}</InfoPart>
        <InfoPart name="self-identification">{failed}</InfoPart>
        <InfoPart name="application-answers">{failed}</InfoPart>
      </>
    );
  }
  return <AnswerCards initial={answers.answers} education={bank.data?.entries ?? []} />;
}

/** The open answers part as bars while the bank is read: the card's head,
 *  then its fields, a label over a field's box. */
function AnswersLoading() {
  return (
    <>
      {(["work-authorization", "self-identification", "application-answers"] as const).map(
        (part, i) => (
          <InfoPart key={part} name={part}>
            <Card role="status" padding="none" className={INFO_CARD}>
              {/* The head's shape (./card-head.tsx), first, as the head is:
                  the card indents what follows it. */}
              <div aria-hidden="true" className="flex items-start gap-3">
                <Skeleton className="rounded-control size-10 shrink-0" />
                <div className="min-w-0 flex-1">
                  <SectionHeadingSkeleton />
                  <Skeleton className="mt-1.5 h-3.5 w-80 max-w-full" />
                  <Skeleton className="mt-2.5 h-3 w-24" />
                </div>
              </div>
              {i !== 1 && (
                <div aria-hidden="true" className={FIELD_GRID}>
                  {Array.from({ length: i === 0 ? 4 : 8 }, (_, j) => (
                    <div key={j} className="flex flex-col gap-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-10 w-full" />
                    </div>
                  ))}
                </div>
              )}
              <span className="sr-only">Loading your application info</span>
            </Card>
          </InfoPart>
        ),
      )}
    </>
  );
}
