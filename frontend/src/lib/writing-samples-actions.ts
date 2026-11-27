"use server";

import { applicantCall, encodeId } from "@/lib/applicant-call";

/**
 * A student's writing samples (KAN-384's API, GET, POST and DELETE
 * /applicants/{id}/writing-samples): up to three pieces of their own
 * writing, from which their own Claude builds a style card through the
 * connector. Application Info's Writing Samples edits them (KAN-387), and the
 * style card too (PUT and DELETE /applicants/{id}/style-card), which every
 * answer written for them follows. Through applicantCall: identity from the
 * session, never an argument.
 */

export type WritingSample = { id: string; text: string };

/** The samples, oldest first, and the style card (null with none); `error` says why on a failed read. */
export async function getWritingSamples(): Promise<{
  samples: WritingSample[] | null;
  styleCard: string | null;
  error: string | null;
}> {
  const { data, error } = await applicantCall<{
    samples: WritingSample[];
    style_card: string | null;
  }>("/writing-samples");
  return { samples: data?.samples ?? null, styleCard: data?.style_card ?? null, error };
}

/** The student's own style card; the API refuses one with no samples, an empty one or one over the limit. */
export async function saveStyleCard(card: string): Promise<{ error: string | null }> {
  const { error } = await applicantCall<null>("/style-card", {
    method: "PUT",
    body: JSON.stringify({ card }),
  });
  return { error };
}

export async function removeStyleCard(): Promise<{ error: string | null }> {
  const { error } = await applicantCall<null>("/style-card", { method: "DELETE" });
  return { error };
}

/** Adds one; the API refuses a fourth, an empty one or one over the limit, with its reason. */
export async function addWritingSample(
  text: string,
): Promise<{ sample: WritingSample | null; error: string | null }> {
  const { data, error } = await applicantCall<WritingSample>("/writing-samples", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  return { sample: data, error };
}

export async function removeWritingSample(id: string): Promise<{ error: string | null }> {
  const { error } = await applicantCall<null>(`/writing-samples/${encodeId(id)}`, {
    method: "DELETE",
  });
  return { error };
}
