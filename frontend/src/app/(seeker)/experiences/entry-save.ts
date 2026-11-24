import {
  addBullet,
  deleteBullet,
  updateBullet,
  updateEntry,
  type BankEntry,
} from "@/lib/bank-actions";

import { bulletMoves } from "./bullet-order";
import { changesOf, type EntryDraft } from "./sections";

export type SaveStep = () => Promise<{ error: string | null }>;

/**
 * The calls that turn a saved entry into the edited draft: its fields in one
 * PATCH first, then the bullet deletes, adds and edits, then the bullets'
 * order. Run them in order; when the first fails nothing has saved, and when
 * a later one fails some changes have, so a retry from the same draft would
 * repeat them. Shared by the bank's editor and intake's visit to an entry
 * already in the bank.
 *
 * **The draft's order is the bank's** (KAN-815): the API adds a bullet last,
 * so the last step moves bullets until the bank holds them as the form
 * showed them, which is the order a new resume starts in. The resume
 * editor's form passes `order: false`, since its order is that resume's
 * alone (`outline-entry.tsx`) and a save there never reorders the bank.
 */
export function editSteps(
  entry: BankEntry,
  draft: EntryDraft,
  { order = true }: { order?: boolean } = {},
): SaveStep[] {
  const { bullets } = draft;
  // Each new bullet's id once its add lands, by its place in the draft
  const added = new Map<number, string>();
  return [
    () => updateEntry(entry.id, changesOf(draft)),
    ...entry.bullets
      .filter((saved) => !bullets.some((b) => b.id === saved.id))
      .map((saved) => () => deleteBullet(saved.id)),
    ...bullets.flatMap((b, i) => {
      if (!b.id)
        return b.text.trim()
          ? [
              async () => {
                const res = await addBullet(entry.id, b.text);
                if (res.data) added.set(i, res.data.id);
                return res;
              },
            ]
          : [];
      const saved = entry.bullets.find((s) => s.id === b.id);
      return saved && saved.text !== b.text ? [() => updateBullet(b.id!, { text: b.text })] : [];
    }),
    ...(order
      ? [
          async () => {
            // The bank's order now: the kept bullets as they were, then the
            // new ones in the order they were added
            const now = [
              ...entry.bullets.map((s) => s.id).filter((id) => bullets.some((b) => b.id === id)),
              ...added.values(),
            ];
            const wanted = bullets.flatMap((b, i) => b.id ?? added.get(i) ?? []);
            for (const { id, position } of bulletMoves(now, wanted)) {
              const { error } = await updateBullet(id, { position });
              if (error) return { error };
            }
            return { error: null };
          },
        ]
      : []),
  ];
}
