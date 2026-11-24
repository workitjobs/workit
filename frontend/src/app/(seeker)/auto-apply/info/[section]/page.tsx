import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LoadFailed } from "@/components/ui/load-failed";
import { getAutofillAnswers } from "@/lib/autofill-answers-actions";
import { getBank } from "@/lib/bank-actions";

import { AnswerBank } from "../answer-bank";
import { AnswersSection } from "../info-screen";
import { infoSection } from "../sections";
import { Transcript } from "../transcript";
import { WorkdaySignup } from "../workday-signup";
import { WritingSamples } from "../writing-samples";

type Props = { params: Promise<{ section: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const section = infoSection((await params).section);
  return {
    title: section ? section.label : "Application Info",
    description: "The answers and files WorkIt fills into your applications.",
  };
}

/**
 * One part of Application Info (../layout.tsx, ../sections.ts): Work
 * Authorization, Voluntary Self-Identification (closed while reading) and
 * Application Answers read the answer bank here, on the server, with the
 * experience bank, whose education entries give Application Answers'
 * School Year (a failed bank read leaves School Year unknown, not the
 * page); Answer Bank (../answer-bank.tsx), Transcript (../transcript.tsx), Writing Samples
 * (../writing-samples.tsx) and Workday Sign-Up (../workday-signup.tsx,
 * which opens the extension's own page) read their own. A failed answers
 * read shows the failed read's card with Try Again (KAN-819), never a card
 * of "Not answered" that would pass for the student's real answers.
 */
export default async function InfoSectionPage({ params }: Props) {
  const section = infoSection((await params).section);
  if (!section) notFound();

  switch (section.key) {
    case "answer-bank":
      return <AnswerBank />;
    case "transcript":
      return <Transcript />;
    case "writing-samples":
      return <WritingSamples />;
    case "workday":
      return <WorkdaySignup />;
  }

  const [answers, bank] = await Promise.all([getAutofillAnswers(), getBank()]);
  if (answers.error != null) {
    return (
      <LoadFailed
        title="Your Answers Aren't Loading Right Now"
        detail={process.env.NODE_ENV === "development" ? answers.error : undefined}
      >
        We couldn&apos;t reach your application answers. Try again in a few minutes.
      </LoadFailed>
    );
  }
  return (
    <AnswersSection
      section={section.key}
      initial={answers.answers}
      education={bank.data?.entries ?? []}
    />
  );
}
