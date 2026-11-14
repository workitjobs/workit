"use client";

import { useState } from "react";

import { PROFILE_QUESTIONS, SELF_ID_KEYS, type AutofillAnswers } from "@/lib/autofill-answers";
import type { BankEntry } from "@/lib/bank-actions";

import { ApplicationAnswers } from "./application-answers";
import { ApplicationQuestions } from "./application-questions";

const WORK_QUESTIONS = PROFILE_QUESTIONS.filter((q) => !SELF_ID_KEYS.includes(q.key));
const SELF_ID_QUESTIONS = PROFILE_QUESTIONS.filter((q) => SELF_ID_KEYS.includes(q.key));

/**
 * The parts of Application Info that read the answer bank
 * (./[section]/page.tsx): Work Authorization, Voluntary Self-Identification
 * and Application Answers. A Save hands the whole bank back (the PATCH
 * answers it), which the card shows; another part reads the bank again
 * when it opens, so it shows the save too.
 */
export function AnswersSection({
  section,
  initial,
  education,
}: {
  section: "work-authorization" | "self-identification" | "application-answers";
  initial: AutofillAnswers;
  /** The experience bank's entries; School Year reads the education ones. */
  education: BankEntry[];
}) {
  const [answers, setAnswers] = useState(initial);

  if (section === "application-answers") {
    return <ApplicationAnswers answers={answers} education={education} onSaved={setAnswers} />;
  }
  return section === "work-authorization" ? (
    <ApplicationQuestions
      id="work-authorization"
      title="Work Authorization"
      description="Whether you can work here and under what status. Most applications ask."
      questions={WORK_QUESTIONS}
      answers={answers}
      onSaved={setAnswers}
    />
  ) : (
    <ApplicationQuestions
      id="self-identification"
      title="Voluntary Self-Identification"
      description="The equal opportunity questions U.S. employers ask. Answering is optional."
      questions={SELF_ID_QUESTIONS}
      concealed
      answers={answers}
      onSaved={setAnswers}
    />
  );
}
