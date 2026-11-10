"use client";

import { PencilSimpleIcon } from "@phosphor-icons/react/ssr";
import { useState, type ReactNode } from "react";

import { DeleteDialog } from "@/app/(seeker)/resumes/delete-confirm";
import { EntryEditor } from "@/app/(seeker)/experiences/entry-editor";
import { EntryRow, MissingFacts } from "@/app/(seeker)/experiences/entry-row";
import { SectionMark } from "@/app/(seeker)/experiences/section-icons";
import { SECTIONS } from "@/app/(seeker)/experiences/sections";
import { SkillGroups } from "@/app/(seeker)/experiences/skill-groups";
import { CheckIcon, FileIcon } from "@/components/icons";
import { ResumeUpload } from "@/components/resume-upload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { IconButton } from "@/components/ui/icon-button";
import type { Section } from "@/lib/bank-actions";
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
 * THE READING LOOKS AND WORKS AS EXPERIENCES DOES (KAN-732): a card per
 * section with the page's own heading and rows (`EntryRow`), each entry's
 * pencil in view, which opens the page's editor (`EntryEditor`: Save Entry,
 * and Delete Entry, which asks in the page's modal, to leave the entry
 * out), the page's
 * warning for what an entry lacks (`MissingFacts`), and the page's skills
 * (`SkillGroups`), purple and grouped, whose × shows in their edit mode.
 * Edits change only the reading in the browser: Save Resume writes it as
 * the student left it, each entry checked again as an Add is.
 *
 * One difference, on purpose: every entry is open, with no chevron, since
 * the student checks all of a reading here and nothing should wait behind a
 * press. While an entry is in the editor the other pencils hide, as on
 * Experiences: a second pencil that moved the editor would drop the first
 * entry's edits, and Save Resume waits for the editor to close anyway. Add
 * Entry stays on Experiences, to keep onboarding short.
 *
 * The step had a row of its own until then, which hid the location, degree,
 * GPA, coursework, issuer and link; then a pencil and a × on every row,
 * which Experiences does not have: it moved Delete into the editor because
 * controls side by side on every row did not say which acted on what
 * (KAN-363); then the section edit mode Experiences had, a press before each
 * edit, which both screens dropped.
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

/** The Experiences page's heading action: a 32px round icon button
 *  (bank-screen's HEADING_ACTION). */
const HEADING_ACTION = "hover:bg-hover size-8 rounded-full";

/** The controls focus goes back to. */
const editId = (index: number) => `preview-entry-${index}-edit`;
const SKILLS_EDIT = "preview-skills-edit";
const SKILLS_DONE = "preview-skills-done";

/** Focus on a control once the list has drawn again: Save Entry, Cancel,
 *  Delete Entry, the pencil and Done each take away the control that had
 *  focus, which then fell to the page's top and lost a keyboard user's place. */
function focusOn(id: string) {
  setTimeout(() => document.getElementById(id)?.focus(), 0);
}

/**
 * What WorkIt read, before anything is saved, drawn as the Experiences page
 * draws a bank (KAN-732): a card per section, each entry with its pencil,
 * which opens the page's editor, whose Delete Entry leaves the entry out
 * once the student says yes. Skills keep the page's edit mode: the heading's
 * pencil shows each skill's ×. Every entry is open, unlike the page's, so
 * the whole reading is in view while the student checks it.
 */
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
  // Skills' edit mode, as on Experiences: their × shows only in it.
  const [editingSkills, setEditingSkills] = useState(false);
  const { entries, duplicate_of: duplicate } = preview;
  const skills = preview.skills.filter((s) => !removedSkills.includes(s.name));

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

  // The entries in the order the cards show them, by their place in the
  // reading, which the editor's calls name.
  const shown = SECTIONS.flatMap((section) =>
    entries.flatMap((entry, index) => (entry.section === section.id ? [index] : [])),
  );

  /** After a delete, focus goes to the next row's pencil, or the one
   *  before, or Skills'. The rows after the deleted one move up one place. */
  function focusAfterDelete(index: number) {
    const at = shown.indexOf(index);
    const next = shown[at + 1] ?? shown[at - 1];
    focusOn(next === undefined ? SKILLS_EDIT : editId(next > index ? next - 1 : next));
  }

  /** A card's heading: the group's mark and name, and its actions. There is
   *  no plus: Add Entry stays on Experiences, to keep onboarding short. */
  const heading = (group: Section | "skills", label: string, actions?: ReactNode) => (
    <div className="flex items-center justify-between gap-3">
      <h3 className="text-subtitle text-ink flex min-w-0 items-center gap-2.5">
        <SectionMark id={group} />
        {label}
      </h3>
      {actions}
    </div>
  );

  return (
    // One note for the whole reading, never a mark on each field: the student
    // looks it over once, not field by field.
    <Field
      Icon={FileIcon}
      label={name}
      tag={false}
      hint="Check that every detail from your resume is here, and make any edits you want before you save."
    >
      {/* Named main, as the Experiences page's column is, so the row and
          the editor lay out as they do there. */}
      <div className="@container/main flex flex-col gap-4">
        {SECTIONS.map((section) => {
          const found = shown.filter((index) => entries[index].section === section.id);
          if (!found.length) return null;
          return (
            <Card as="section" key={section.id} aria-label={section.label}>
              {heading(section.id, section.label)}
              <ul role="list" className="divide-border-subtle mt-2 flex flex-col divide-y">
                {found.map((index) => {
                  const entry = entries[index];
                  return (
                    <li key={index} className="py-3">
                      {editing === index ? (
                        <EditReadEntry
                          entry={entry}
                          onSave={(next) => {
                            onSaveEntry(index, next);
                            focusOn(editId(index));
                          }}
                          onCancel={() => {
                            onEditEntry(null);
                            focusOn(editId(index));
                          }}
                          onDelete={() => {
                            onLeaveOutEntry(index);
                            focusAfterDelete(index);
                          }}
                        />
                      ) : (
                        <EntryRow
                          entry={rowOfPreview(entry)}
                          open
                          actions={
                            editing === null && (
                              <IconButton
                                id={editId(index)}
                                label={`Edit ${entry.title}`}
                                tooltip="Edit this entry"
                                onClick={() => onEditEntry(index)}
                              >
                                <PencilSimpleIcon aria-hidden className="size-4" />
                              </IconButton>
                            )
                          }
                          note={
                            <>
                              {entry.replaces.length > 0 && (
                                // Inert, not a status colour: replacing is no stage and
                                // owes nothing (frontend/docs/design.md, colour meanings).
                                <div className="mt-1.5">
                                  <Badge variant="tag" tone="inert">
                                    Replaces Earlier Copy
                                  </Badge>
                                </div>
                              )}
                              <MissingFacts entry={entry} />
                            </>
                          }
                        />
                      )}
                    </li>
                  );
                })}
              </ul>
            </Card>
          );
        })}
        {/* The headings the bank has no section for (KAN-498): each saves as
            a section of its own, as plain lines */}
        {entries
          .filter((e) => e.section === "custom")
          .map((entry, i) => (
            <section key={`custom-${i}`} aria-label={entry.section_name ?? entry.title}>
              <h3 className="text-caption text-ink-muted mb-2 uppercase">
                {entry.section_name ?? entry.title}
              </h3>
              <ul className="text-body text-ink flex flex-col gap-1">
                {entry.bullets.map((line, j) => (
                  <li key={j}>{line}</li>
                ))}
              </ul>
            </section>
          ))}
        {skills.length > 0 && (
          <Card as="section" aria-label="Skills">
            {heading(
              "skills",
              "Skills",
              editingSkills ? (
                <Button
                  id={SKILLS_DONE}
                  variant="section"
                  onClick={() => {
                    setEditingSkills(false);
                    focusOn(SKILLS_EDIT);
                  }}
                >
                  Done
                </Button>
              ) : (
                <IconButton
                  id={SKILLS_EDIT}
                  label="Edit Skills"
                  tooltip="Edit this section"
                  className={HEADING_ACTION}
                  onClick={() => {
                    setEditingSkills(true);
                    focusOn(SKILLS_DONE);
                  }}
                >
                  <PencilSimpleIcon aria-hidden className="size-5" />
                </IconButton>
              ),
            )}
            <SkillGroups
              skills={skills}
              keyOf={(skill) => skill.name}
              editable={editingSkills}
              onRemove={(skill) => onRemoveSkill(skill.name)}
            />
          </Card>
        )}
      </div>
    </Field>
  );
}

/**
 * An entry of the reading open in the page's editor, as Experiences'
 * `EditEntry` is: Delete Entry asks first, in the same modal
 * (`DeleteDialog`), then leaves the entry out of the reading. The question
 * says the entry is not saved and the file stays as it is, since nothing of
 * the reading is saved yet.
 */
function EditReadEntry({
  entry,
  onSave,
  onCancel,
  onDelete,
}: {
  entry: PreviewEntry;
  onSave: (entry: PreviewEntry) => void;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  return (
    <>
      <EntryEditor
        initial={draftOfPreview(entry)}
        onSave={(draft) => onSave(previewOfDraft(draft, entry))}
        onCancel={onCancel}
        onDelete={() => setConfirming(true)}
      />
      {confirming && (
        <DeleteDialog
          title={`Delete ${entry.title || "this entry"}?`}
          label="Delete Entry"
          onDelete={onDelete}
          onKeep={() => setConfirming(false)}
        >
          {entry.bullets.length > 0 && "Its bullets are deleted too. "}
          It is not saved to your Experiences. Your file does not change.
        </DeleteDialog>
      )}
    </>
  );
}
