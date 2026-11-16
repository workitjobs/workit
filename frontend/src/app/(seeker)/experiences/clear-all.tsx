import type { BankResume } from "@/lib/bank-actions";

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
 * needs no call of its own, unlike Delete Entry's. Every Clear All asks
 * across its list's foot: a section's (`section-dialog.tsx`, KAN-740), and
 * Skills' in their dialog (`skills-dialog.tsx`, KAN-816), which asked in a
 * modal of its own while Skills edited on the card. Skills' Delete Group
 * reads the same words for where its skills go.
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
