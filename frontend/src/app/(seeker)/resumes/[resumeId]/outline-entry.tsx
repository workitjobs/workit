"use client";

import { useState, type RefObject } from "react";

import { EntryDialog, type SaveOutcome } from "@/app/(seeker)/experiences/entry-dialog";
import { editSteps } from "@/app/(seeker)/experiences/entry-save";
import { usedIn } from "@/app/(seeker)/experiences/holdings";
import { emptyDraft, NOUNS, type EntryDraft } from "@/app/(seeker)/experiences/sections";
import { createEntry, type Bank, type BankEntry, type EntrySection } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";

import { resumeDraft, writesBank } from "./entry-order";

/** What a save leaves for the editor: the bank to read again when the save
 *  wrote it, and this resume's bullets in order, each on or off (an entry
 *  edited; a new one has none). */
export type EntrySaved = {
  entryId: string | null;
  bankChanged: boolean;
  bullets?: { id?: string; text: string; off?: boolean }[];
  /** A school's GPA and coursework switches for this resume. */
  shows?: { gpa: boolean; coursework: boolean };
};

/**
 * The Sections outline's entry form (KAN-586): the Experiences page's own
 * form (`EntryDialog`), opened from an entry's row or its Edit, or a
 * section's +, so a student changes dates, degree or location, adds a job,
 * or orders and picks an entry's bullets without leaving the editor.
 *
 * **Two scopes, kept apart.** The fields and the bullets' words are the
 * bank's (until KAN-800 makes resume edits local): a save changes them on
 * every resume that shows the entry, and the form names those resumes over
 * its foot. **The bullets' order and their check boxes are this resume's**
 * (`resumeMode`): the form opens on this resume's order, every bullet the
 * bank holds listed, the ones this resume leaves out unticked, and the
 * editor saves them as one choice change with Undo (`EntrySaved`). The bank
 * is written only when a field or a word changed, so a reorder alone never
 * marks the bank changed. There is no ×, and no Delete, for a saved
 * bullet or the entry: on a resume, off means this resume only, and
 * deleting from the bank stays on the Experiences page.
 */
export function OutlineEntryDialog({
  bank,
  choices,
  resumeId,
  target,
  section,
  customSectionId = null,
  returnTo,
  onClose,
  onSaved,
}: {
  bank: Bank;
  choices: Choices;
  resumeId: string;
  /** The entry to edit, or null for a new one. */
  target: BankEntry | null;
  section: EntrySection;
  customSectionId?: string | null;
  returnTo: RefObject<() => HTMLElement | null>;
  onClose: () => void;
  onSaved: (saved: EntrySaved) => Promise<void>;
}) {
  const noun =
    section === "custom"
      ? (bank.sections.find((s) => s.id === customSectionId)?.name ?? "Entry")
      : NOUNS[section][0];
  const others = target ? usedIn(resumeId, target, bank.resumes ?? []) : [];
  const initial = target ? resumeDraft(target, choices) : emptyDraft(section, customSectionId);
  // A school's two switches, this resume's (its choice row), saved with the
  // bullets' order and boxes
  const row = target && choices.entries.find((c) => c.entry_id === target.id);
  const [shows, setShows] = useState({
    gpa: row?.show_gpa ?? true,
    coursework: row?.show_coursework ?? true,
  });

  async function save(draft: EntryDraft, asNew: boolean): Promise<SaveOutcome> {
    if (!target) {
      const { bullets, ...fields } = draft;
      const res = await createEntry(
        fields,
        bullets.map((b) => b.text),
        asNew,
        resumeId,
      );
      if (res.duplicate) return { duplicate: res.duplicate };
      if (!res.entry) return { error: res.error ?? "Your entry didn't save. Try again." };
      await onSaved({ entryId: res.entry.id, bankChanged: true });
      return { saved: true };
    }
    const bankChanged = writesBank(target, draft);
    if (bankChanged) {
      for (const [i, step] of editSteps(target, draft).entries()) {
        const { error } = await step();
        if (!error) continue;
        // Nothing saved yet: the form stays open to fix it
        if (i === 0) return { error };
        // Some changes saved: a retry from this form would repeat them
        await onSaved({ entryId: target.id, bankChanged: true });
        return { error: `Some changes did not save: ${error}` };
      }
    }
    await onSaved({ entryId: target.id, bankChanged, bullets: draft.bullets, shows });
    return { saved: true };
  }

  return (
    <EntryDialog
      title={`${target ? "Edit" : "Add"} ${noun}`}
      initial={initial}
      resumeMode={target !== null}
      resumeSwitches={
        target?.section === "education" && row
          ? { gpa: shows.gpa, coursework: shows.coursework, onChange: setShows }
          : undefined
      }
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
