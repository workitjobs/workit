"use client";

import { useState } from "react";

import type { BankResume } from "@/lib/bank-actions";

import { DeleteDialog } from "../resumes/delete-confirm";
import { builtShowing, uploadsOwning, type Pick } from "./holdings";

type ClearAllItems = {
  items: { id: string; resume_ids: string[] }[];
  resumes: BankResume[];
  /** One and many: ["Projects entry", "Projects entries"]. */
  noun: readonly [string, string];
  /** Entries carry bullets, which go with them. */
  bullets?: boolean;
  pick: Pick;
};

/**
 * Clear All's question (KAN-352): it deletes every entry or skill a section
 * shows, in one call, from the bank, as Delete Entry does: the items come
 * off every built resume that shows them, and under a built resume's pick
 * they leave the uploads that own them too (ADR 0005), which the line names.
 * The counts read the bank's `resume_ids` (`holdings.ts`), so the question
 * needs no call of its own, unlike Delete Entry's. A section's Clear All asks
 * in its list's foot (`section-dialog.tsx`, KAN-740); Skills' asks in a
 * modal (`ClearAll`, below).
 */
export function clearAllWords({ items, resumes, noun, bullets = false, pick }: ClearAllItems) {
  const one = items.length === 1;
  const showing = builtShowing(items, resumes);
  const owners = uploadsOwning(pick, items, resumes);
  const them = one ? "it" : "them";
  const count = one ? "this" : items.length === 2 ? "both" : `all ${items.length}`;
  return {
    question: `Delete ${count} ${noun[one ? 0 : 1]}?`,
    detail:
      (bullets ? (one ? "Its bullets are deleted too. " : "Their bullets are deleted too. ") : "") +
      (owners ? `${one ? "It is" : "They are"} deleted from ${owners} too. ` : "") +
      (showing === 0
        ? `No built resume shows ${them}.`
        : `${one ? "It comes" : "They come"} off ${showing === 1 ? "the 1 built resume that shows" : `all ${showing} built resumes that show`} ${them}.`),
  };
}

/** Skills' Clear All, a modal since KAN-732 (`DeleteDialog`): the Skills
 *  card is on the page, not in a dialog, so its question may be one. */
export function ClearAll({
  remove,
  onCleared,
  onKeep,
  ...what
}: ClearAllItems & {
  remove: (ids: string[]) => Promise<{ error: string | null }>;
  onCleared: () => void;
  onKeep: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { question, detail } = clearAllWords(what);

  async function clear() {
    setBusy(true);
    setError(null);
    const { error } = await remove(what.items.map((i) => i.id));
    setBusy(false);
    if (error) return setError(error);
    onCleared();
  }

  return (
    <DeleteDialog
      title={question}
      label="Clear All"
      busy={busy}
      error={error}
      onDelete={clear}
      onKeep={onKeep}
    >
      {detail}
    </DeleteDialog>
  );
}
