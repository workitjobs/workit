"use server";

import type { FactValue, SavedAnswer, SavedFact } from "@/lib/app-answers";
import { appCall } from "@/lib/applicant-call";

/**
 * What WorkIt Auto Apply kept from the student's Needs You answers (W11's
 * GET /apply-app/answered and PATCH /apply-app/profile, the app's own
 * routes): Application Info reads and edits them. Through appCall: identity
 * from the session, never an argument.
 */

export async function getAppAnswers(): Promise<{
  answered: SavedAnswer[] | null;
  facts: SavedFact[] | null;
  error: string | null;
}> {
  const { data, error } = await appCall<{ answered: SavedAnswer[]; facts: SavedFact[] }>(
    "/answered",
  );
  return { answered: data?.answered ?? null, facts: data?.facts ?? null, error };
}

/** One answer or fact saved (`set`) or taken out (`remove`), by its question or its dotted key. */
export async function changeAppAnswers(change: {
  kind: "answered" | "fact";
  id: string;
  set?: FactValue;
  remove?: boolean;
}): Promise<{ error: string | null }> {
  const { kind, id, set, remove } = change;
  const body =
    kind === "answered"
      ? { answered: set === undefined ? {} : { [id]: set }, remove_answered: remove ? [id] : [] }
      : { facts: set === undefined ? {} : { [id]: set }, remove_facts: remove ? [id] : [] };
  const { error } = await appCall<null>("/profile", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  return { error };
}
