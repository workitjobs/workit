"use server";

import type { BankEntry } from "@/lib/answer-bank";
import { applicantCall } from "@/lib/applicant-call";

/**
 * A student's Answer bank (W11's API, GET and PATCH
 * /applicants/{id}/answer-bank): Application Info's Answer Bank reads and
 * edits it. Only WorkIt's rule decides what enters, so a save can come back
 * kept out, with the rule's reason. Through applicantCall: identity from
 * the session, never an argument.
 */

/** Every entry; `error` says why on a failed read. */
export async function getAnswerBank(): Promise<{
  entries: BankEntry[] | null;
  error: string | null;
}> {
  const { data, error } = await applicantCall<Record<string, BankEntry>>("/answer-bank");
  return { entries: data ? Object.values(data) : null, error };
}

/** One entry to save: `review` true keeps a draft flagged; `choice` lets the rule read its question alone. */
export type BankSave = {
  question: string;
  answer: string | string[];
  review: boolean;
  choice?: boolean;
};

/** Saves or deletes one answer. `keptOut` is the rule's reason when it kept a save out of the bank. */
export async function changeAnswerBank(change: {
  save?: BankSave;
  remove?: string;
}): Promise<{ keptOut: string | null; error: string | null }> {
  const { data, error } = await applicantCall<{
    version: number;
    kept_out: Record<string, string>;
  }>("/answer-bank", {
    method: "PATCH",
    body: JSON.stringify({
      set: change.save ? [change.save] : [],
      delete: change.remove ? [change.remove] : [],
    }),
  });
  return { keptOut: data ? (Object.values(data.kept_out)[0] ?? null) : null, error };
}
