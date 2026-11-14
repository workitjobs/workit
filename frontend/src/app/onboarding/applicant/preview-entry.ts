import type { EntryDraft } from "@/app/(seeker)/experiences/sections";
import type { PreviewEntry } from "@/lib/resume-actions";

/**
 * A parse preview's entries (KAN-372) in the shapes the Experiences page's
 * own row and editor take (KAN-732): `EntryRow` draws a preview entry and
 * `EntryEditor` edits it, as they draw and edit a bank entry, so the two
 * screens look and work alike. A preview entry has no ids, since nothing is
 * saved yet; its bullets are plain text. Types only from elsewhere, so the
 * tests run without the app's path aliases.
 */

/** A preview entry as the shared row draws it: each bullet with an id (its place). */
export function rowOfPreview(entry: PreviewEntry) {
  return { ...entry, bullets: entry.bullets.map((text, i) => ({ id: String(i), text })) };
}

/** The editor's draft of a preview entry: its fields, each bullet a box,
 *  and not the rows it replaces, which the editor has no field for. */
export function draftOfPreview(entry: PreviewEntry): EntryDraft {
  const draft: EntryDraft & { replaces?: string[] } = {
    ...entry,
    bullets: entry.bullets.map((text) => ({ text })),
  };
  delete draft.replaces;
  return draft;
}

/** The server's match for a confirm's replacing (`bank.upload_matches`):
 *  section, title and organization, ignoring case and surrounding spaces. */
function matchKey(entry: Pick<PreviewEntry, "section" | "title" | "organization">): string {
  return [
    entry.section,
    entry.title.trim().toLowerCase(),
    (entry.organization ?? "").trim().toLowerCase(),
  ].join("\n");
}

/**
 * A preview entry from the editor's draft, which the save sends back as the
 * student left it. It keeps the rows the original replaces only while its
 * match stays the same: a new title or organization may match other rows,
 * which the save works out again, so the preview stops naming any.
 */
export function previewOfDraft(draft: EntryDraft, original: PreviewEntry): PreviewEntry {
  const { bullets, ...fields } = draft;
  const entry = { ...fields, bullets: bullets.map((b) => b.text.trim()).filter(Boolean) };
  return {
    ...entry,
    // A custom section's name (KAN-498): the editor has no field for it, and
    // the save needs it to make the section
    section_name: original.section_name,
    replaces: matchKey(entry) === matchKey(original) ? original.replaces : [],
  };
}
