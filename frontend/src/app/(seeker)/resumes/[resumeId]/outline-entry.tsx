"use client";

import type { RefObject } from "react";

import { EntryDialog, type SaveOutcome } from "@/app/(seeker)/experiences/entry-dialog";
import { editSteps } from "@/app/(seeker)/experiences/entry-save";
import { usedIn } from "@/app/(seeker)/experiences/holdings";
import { draftOf, emptyDraft, NOUNS, type EntryDraft } from "@/app/(seeker)/experiences/sections";
import { createEntry, type Bank, type BankEntry, type EntrySection } from "@/lib/bank-actions";

/**
 * The Sections outline's entry form (KAN-586): the Experiences page's own
 * form (`EntryDialog`), opened from an entry's Edit or a section's Add
 * Entry, so a student changes dates, degree or location, or adds a job,
 * without leaving the editor.
 *
 * **An edit is the bank's** (until KAN-800 makes resume edits local): it
 * changes the entry on every resume that shows it, and the form names those
 * other resumes over its foot, as the Experiences page's does. **A new entry
 * is this resume's**: it is saved into the bank with this resume as its
 * holder (`createEntry`'s `resumeId`), which gives it a shown choice row at
 * the end of its section. The bank is read again after a save (`onSaved`).
 * It has no Delete: on a resume, Remove takes an entry off this resume only,
 * and deleting from the bank stays on the Experiences page.
 */
export function OutlineEntryDialog({
  bank,
  resumeId,
  target,
  section,
  customSectionId = null,
  returnTo,
  onClose,
  onSaved,
}: {
  bank: Bank;
  resumeId: string;
  /** The entry to edit, or null for a new one. */
  target: BankEntry | null;
  section: EntrySection;
  customSectionId?: string | null;
  returnTo: RefObject<() => HTMLElement | null>;
  onClose: () => void;
  /** Reads the bank and the choices again; an error to show, or null. */
  onSaved: () => Promise<void>;
}) {
  const noun =
    section === "custom"
      ? (bank.sections.find((s) => s.id === customSectionId)?.name ?? "Entry")
      : NOUNS[section][0];
  const others = target ? usedIn(resumeId, target, bank.resumes ?? []) : [];

  async function save(draft: EntryDraft, asNew: boolean): Promise<SaveOutcome> {
    if (target) {
      for (const [i, step] of editSteps(target, draft).entries()) {
        const { error } = await step();
        if (!error) continue;
        // Nothing saved yet: the form stays open to fix it
        if (i === 0) return { error };
        // Some changes saved: a retry from this form would repeat them
        await onSaved();
        return { error: `Some changes did not save: ${error}` };
      }
    } else {
      const { bullets, ...fields } = draft;
      const res = await createEntry(
        fields,
        bullets.map((b) => b.text).filter((text) => text.trim()),
        asNew,
        resumeId,
      );
      if (res.duplicate) return { duplicate: res.duplicate };
      if (!res.entry) return { error: res.error ?? "Your entry didn't save. Try again." };
    }
    await onSaved();
    return { saved: true };
  }

  return (
    <EntryDialog
      title={`${target ? "Edit" : "Add"} ${noun}`}
      initial={target ? draftOf(target) : emptyDraft(section, customSectionId)}
      note={
        others.length > 0 && (
          <p className="rounded-control bg-well text-note text-ink-muted px-3 py-2">
            Saving also changes this entry on {others.map((r) => r.name).join(", ")}.
          </p>
        )
      }
      save={save}
      returnTo={returnTo}
      onClose={onClose}
    />
  );
}
