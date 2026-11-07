"use client";

import { PencilSimpleIcon, XIcon } from "@phosphor-icons/react/ssr";

import { EntryEditor } from "@/app/(seeker)/experiences/entry-editor";
import { EntryRow } from "@/app/(seeker)/experiences/entry-row";
import { SECTIONS } from "@/app/(seeker)/experiences/sections";
import { CheckIcon, FileIcon } from "@/components/icons";
import { ResumeUpload } from "@/components/resume-upload";
import { Badge } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/icon-button";
import type { PreviewEntry, ResumePreview } from "@/lib/resume-actions";

import { draftOfPreview, previewOfDraft, rowOfPreview } from "./preview-entry";
import { Field } from "./role-step";

/**
 * Onboarding's resume step (KAN-372, ADR 0006). The student picks a file and
 * Read Resume shows what WorkIt read in it (AI first, the parser behind it,
 * KAN-732), with nothing saved yet (POST .../resumes/preview). Save Resume
 * then uploads the same file with `replace=matching` and that reading, so
 * the reading lands in the experience bank and
 * replaces, rather than copies, what an earlier upload holds of the same
 * entries. Each entry and skill that would replace one says so here, before
 * the student agrees. Each skill has a × (KAN-369): a skill taken out is not
 * saved, and no later reading adds it again. The footer's buttons live in
 * ./onboarding-form, which owns the step's state.
 *
 * THE READING LOOKS AND WORKS AS EXPERIENCES DOES (KAN-732). Each entry is the
 * Experiences page's own row (`EntryRow`): closed it shows the title, place,
 * dates and a school's degree; open, the rest and its bullets. Edit opens the
 * page's own editor (`EntryEditor`, "Done" in place of "Save Entry"), and
 * Leave Out drops the entry, as a skill's × drops a skill. Both change only
 * the reading in the browser: Save Resume writes it as the student left it,
 * each entry checked again as an Add is. The step had its own row until
 * then, which hid the location, degree, GPA, coursework, issuer and link, so
 * the student could not check them, and fixing an entry meant saving it
 * first. Add Entry stays on Experiences, to keep onboarding short.
 */
export function ResumeStep({
  file,
  onFileChange,
  onRemove,
  reading,
  preview,
  removedSkills,
  onRemoveSkill,
  editing,
  onEditEntry,
  onSaveEntry,
  onLeaveOutEntry,
  savedName,
}: {
  file: File | null;
  onFileChange: (file: File) => void;
  onRemove: () => void;
  /** Read Resume is in flight. */
  reading: boolean;
  /** The picked file's reading, once Read Resume answered, with the student's edits. */
  preview: ResumePreview | null;
  /** The skills the student took out of the reading (×). */
  removedSkills: readonly string[];
  onRemoveSkill: (name: string) => void;
  /** The entry open in the editor, by its place in the reading. */
  editing: number | null;
  onEditEntry: (index: number | null) => void;
  /** Done in the editor: the entry as the student left it. */
  onSaveEntry: (index: number, entry: PreviewEntry) => void;
  onLeaveOutEntry: (index: number) => void;
  /** The file this visit saved, if any. */
  savedName: string | null;
}) {
  if (file && preview)
    return (
      <Reading
        name={file.name}
        preview={preview}
        removedSkills={removedSkills}
        onRemoveSkill={onRemoveSkill}
        editing={editing}
        onEditEntry={onEditEntry}
        onSaveEntry={onSaveEntry}
        onLeaveOutEntry={onLeaveOutEntry}
      />
    );
  return (
    <>
      {savedName && (
        <p className="text-body text-positive-ink bg-positive-tint rounded-control mb-6 flex items-center gap-2 px-3.5 py-2.5">
          <CheckIcon className="size-4 shrink-0" />
          Saved {savedName}. Its entries are in your Experiences.
        </p>
      )}
      <Field
        Icon={FileIcon}
        label="Resume"
        hint={
          savedName
            ? "Have a newer version? Read it the same way."
            : "Nothing is saved until you check what WorkIt found."
        }
      >
        <ResumeUpload file={file} onFileChange={onFileChange} onRemove={onRemove} busy={reading} />
      </Field>
    </>
  );
}

function count(n: number, one: string, many = `${one}s`) {
  return `${n} ${n === 1 ? one : many}`;
}

/** The Edit button of the reading's entry at `index`. */
const editId = (index: number) => `preview-entry-${index}-edit`;

/** Focus back on an entry's Edit button once the list has drawn again: Done,
 *  Cancel and Leave Out each take away the control that had focus, which
 *  then fell to the page's top and lost a keyboard user's place. */
function focusEdit(index: number) {
  setTimeout(() => document.getElementById(editId(index))?.focus(), 0);
}

/** What WorkIt read, by section, before anything is saved, each entry in the
 *  Experiences page's own row (`EntryRow`) and editor (`EntryEditor`). */
function Reading({
  name,
  preview,
  removedSkills,
  onRemoveSkill,
  editing,
  onEditEntry,
  onSaveEntry,
  onLeaveOutEntry,
}: {
  name: string;
  preview: ResumePreview;
  removedSkills: readonly string[];
  onRemoveSkill: (name: string) => void;
  editing: number | null;
  onEditEntry: (index: number | null) => void;
  onSaveEntry: (index: number, entry: PreviewEntry) => void;
  onLeaveOutEntry: (index: number) => void;
}) {
  const { entries, duplicate_of: duplicate } = preview;
  const skills = preview.skills.filter((s) => !removedSkills.includes(s.name));
  const replacing =
    entries.filter((e) => e.replaces.length).length +
    skills.filter((s) => s.replaces.length).length;

  if (duplicate) {
    return (
      <Field Icon={FileIcon} label="Already Uploaded">
        <p className="text-subtitle text-ink font-normal">
          You uploaded this resume before, as {duplicate.name}. Its entries are already in your
          Experiences, so there is nothing new to save.
        </p>
      </Field>
    );
  }

  if (entries.length === 0 && skills.length === 0) {
    return (
      <Field Icon={FileIcon} label="What WorkIt Found">
        <p className="text-subtitle text-ink font-normal">
          WorkIt couldn&apos;t find any entries in {name}. You can still save it, and add your
          experiences later on the Experiences page.
        </p>
      </Field>
    );
  }

  return (
    <Field
      Icon={FileIcon}
      label={name}
      tag={false}
      hint={
        `${count(entries.length, "entry", "entries")} and ${count(skills.length, "skill")}. ` +
        (replacing
          ? `${count(replacing, "item")} will replace their copies from an earlier upload. `
          : "") +
        "Edit or leave out anything before you save."
      }
    >
      <div className="flex flex-col gap-6">
        {SECTIONS.map((section) => {
          // Each entry keeps its place in the reading, which Edit and Leave Out name.
          const found = entries
            .map((entry, index) => ({ entry, index }))
            .filter(({ entry }) => entry.section === section.id);
          if (!found.length) return null;
          return (
            <section key={section.id} aria-label={section.label}>
              <h3 className="text-caption text-ink-muted mb-2 uppercase">{section.label}</h3>
              <ul
                role="list"
                className="border-border-subtle divide-border-subtle rounded-card flex flex-col divide-y border px-4"
              >
                {found.map(({ entry, index }) => (
                  <li key={index} className="py-3">
                    {editing === index ? (
                      <EntryEditor
                        initial={draftOfPreview(entry)}
                        saveLabel="Done"
                        onSave={(draft) => {
                          onSaveEntry(index, previewOfDraft(draft, entry));
                          focusEdit(index);
                        }}
                        onCancel={() => {
                          onEditEntry(null);
                          focusEdit(index);
                        }}
                      />
                    ) : (
                      <EntryRow
                        entry={rowOfPreview(entry)}
                        actions={
                          // Hidden while another entry is open, so one edit is open at a time.
                          editing === null && (
                            <span className="flex shrink-0 items-center gap-1">
                              <IconButton
                                id={editId(index)}
                                label={`Edit ${entry.title}`}
                                tooltip="Edit this entry"
                                onClick={() => onEditEntry(index)}
                              >
                                <PencilSimpleIcon aria-hidden className="size-4" />
                              </IconButton>
                              <IconButton
                                label={`Leave out ${entry.title}`}
                                tooltip="Leave this entry out"
                                onClick={() => {
                                  onLeaveOutEntry(index);
                                  // The next entry takes this place; the last one's goes to the one before.
                                  focusEdit(index < entries.length - 1 ? index : index - 1);
                                }}
                              >
                                <XIcon aria-hidden className="size-4" />
                              </IconButton>
                            </span>
                          )
                        }
                        note={
                          entry.replaces.length > 0 && (
                            // Inert, not a status colour: replacing is no stage and owes
                            // nothing (frontend/docs/design.md, colour meanings).
                            <div className="mt-1.5 pl-6">
                              <Badge variant="tag" tone="inert">
                                Replaces Earlier Copy
                              </Badge>
                            </div>
                          )
                        }
                      />
                    )}
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
        {skills.length > 0 && (
          <section aria-label="Skills">
            <h3 className="text-caption text-ink-muted mb-2 uppercase">Skills</h3>
            <ul className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <li
                  key={skill.name}
                  className="rounded-control text-note text-ink border-border-subtle inline-flex items-center gap-1.5 border px-2 py-1"
                >
                  {skill.name}
                  <IconButton
                    label={`Remove ${skill.name}`}
                    tooltip="Leave this skill out"
                    onClick={() => onRemoveSkill(skill.name)}
                  >
                    <XIcon aria-hidden className="size-3" />
                  </IconButton>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Field>
  );
}
