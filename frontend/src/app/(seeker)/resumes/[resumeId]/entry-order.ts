/**
 * The resume editor's entry form, the pure half (KAN-586): the draft it
 * opens on, in this resume's bullet order, and whether a save writes the
 * bank (`outline-entry.tsx`). Tested in `entry-order.test.ts`.
 */

import type { BankEntry } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";

import { draftOf, savable, type EntryDraft } from "../../experiences/sections.ts";

/** The entry's draft in this resume's order: the bullets it shows, by
 *  position, then the ones it leaves out (`off`), in the bank's order. */
export function resumeDraft(target: BankEntry, choices: Choices): EntryDraft {
  const choice = new Map(choices.bullets.map((c) => [c.bullet_id, c]));
  const draft = draftOf(target);
  const shown = target.bullets
    .map((b, i) => ({ b, i, c: choice.get(b.id) }))
    .filter((x) => x.c?.shown)
    .sort((a, z) => a.c!.position - z.c!.position || a.i - z.i)
    .map((x) => ({ id: x.b.id, text: x.b.text }));
  const off = target.bullets
    .filter((b) => !choice.get(b.id)?.shown)
    .map((b) => ({ id: b.id, text: b.text, off: true }));
  return { ...draft, bullets: [...shown, ...off] };
}

/** Whether a save writes the bank: a field changed, a bullet's words
 *  changed, or a new bullet has words. Order and `off` never do. */
export function writesBank(target: BankEntry, draft: EntryDraft): boolean {
  const { bullets: before, ...was } = savable(draftOf(target));
  const { bullets: after, ...now } = savable(draft);
  if (JSON.stringify(was) !== JSON.stringify(now)) return true;
  const text = new Map(before.map((b) => [b.id, b.text]));
  return after.some((b) => (b.id ? text.get(b.id) !== b.text : b.text.trim() !== ""));
}
