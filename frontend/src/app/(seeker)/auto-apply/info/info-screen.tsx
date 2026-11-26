"use client";

import { useState } from "react";

import { PROFILE_QUESTIONS, SELF_ID_KEYS, type AutofillAnswers } from "@/lib/autofill-answers";
import type { BankEntry } from "@/lib/bank-actions";

import { ApplicationAnswers } from "./application-answers";
import { ApplicationQuestions } from "./application-questions";
import { InfoPart } from "./info-part";

const WORK_QUESTIONS = PROFILE_QUESTIONS.filter((q) => !SELF_ID_KEYS.includes(q.key));
const SELF_ID_QUESTIONS = PROFILE_QUESTIONS.filter((q) => SELF_ID_KEYS.includes(q.key));

/**
 * The three parts of Application Info that read the answer bank
 * (./layout.tsx): Work Authorization, Voluntary Self-Identification and
 * Application Answers, each its own part (./info-part.tsx). One copy of
 * the bank for all three: a Save hands the whole bank back (the PATCH
 * answers it), and every card counts its answers from it.
 */
export function AnswerCards({
  initial,
  education,
}: {
  initial: AutofillAnswers;
  /** The experience bank's entries; School Year reads the education ones. */
  education: BankEntry[];
}) {
  const [answers, setAnswers] = useState(initial);
  return (
    <>
      <InfoPart name="work-authorization">
        <ApplicationQuestions
          id="work-authorization"
          title="Work Authorization"
          description="Whether you can work here and under what status. Most applications ask."
          questions={WORK_QUESTIONS}
          answers={answers}
          onSaved={setAnswers}
        />
      </InfoPart>
      <InfoPart name="self-identification">
        <ApplicationQuestions
          id="self-identification"
          title="Voluntary Self-Identification"
          description="The equal opportunity questions U.S. employers ask. Answering is optional."
          questions={SELF_ID_QUESTIONS}
          concealed
          answers={answers}
          onSaved={setAnswers}
        />
      </InfoPart>
      <InfoPart name="application-answers">
        <ApplicationAnswers answers={answers} education={education} onSaved={setAnswers} />
      </InfoPart>
    </>
  );
}
