"use client";

import { PencilSimpleIcon, XIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { EntryEditor } from "@/app/(seeker)/experiences/entry-editor";
import { EntryRow } from "@/app/(seeker)/experiences/entry-row";
import { SectionMark } from "@/app/(seeker)/experiences/section-icons";
import { SECTIONS } from "@/app/(seeker)/experiences/sections";
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
 * section with the page's own heading and rows (`EntryRow`), and the page's
 * edit mode (KAN-363): the heading's pencil makes each entry show its own,
 * which opens the page's editor (`EntryEditor`, Save Entry, Delete Entry
 * to leave it out), and in Skills each skill its ×. One difference, on
 * purpose: every entry is open, with no chevron, since the student checks
 * all of a reading here and nothing should wait behind a press. Edits change
 * only the reading in the browser: Save Resume writes it as the student left
 * it, each entry checked again as an Add is. The step had a row of its own
 * until then, which hid the location, degree, GPA, coursework, issuer and
 * link; then a pencil and a × on every row, which Experiences does not
 * have: it moved Delete into the editor because controls side by side on
 * every row did not say which acted on what (KAN-363). Add Entry stays on
 * Experiences, to keep onboarding short.
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
const doneId = (group: Group) => `preview-${group}-done`;

/** Focus back on a control once the list has drawn again: Save Entry,
 *  Cancel and Delete Entry each take away the control that had focus, which
 *  then fell to the page's top and lost a keyboard user's place. */
function focusOn(id: string) {
  setTimeout(() => document.getElementById(id)?.focus(), 0);
}

type Group = Section | "skills";

/**
 * What WorkIt read, before anything is saved, drawn as the Experiences page
 * draws a bank (KAN-732): a card per section, its heading's pencil opening
 * the section's edit mode, where each entry shows its own pencil and the
 * heading's pencil gives way to Done. The pencil opens the page's editor,
 * whose Delete Entry leaves the entry out. Every entry is open, unlike the
 * page's, so the whole reading is in view while the student checks it.
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
  // The section in edit mode, as one card at a time is on Experiences.
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
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

  /** A card's heading: the group's mark and name, and its pencil, or Done in
   *  edit mode. Nothing while an entry is open in the editor. There is no
   *  plus: Add Entry stays on Experiences, to keep onboarding short. */
  const heading = (group: Group, label: string) => (
    <div className="flex items-center justify-between gap-3">
      <h3 className="text-subtitle text-ink flex min-w-0 items-center gap-2.5">
        <SectionMark id={group} />
        {label}
      </h3>
      {editing === null &&
        (editingGroup === group ? (
          <Button id={doneId(group)} variant="section" onClick={() => setEditingGroup(null)}>
            Done
          </Button>
        ) : (
          <IconButton
            label={`Edit ${label}`}
            tooltip="Edit this section"
            className={HEADING_ACTION}
            onClick={() => setEditingGroup(group)}
          >
            <PencilSimpleIcon aria-hidden className="size-5" />
          </IconButton>
        ))}
    </div>
  );

  return (
    <Field Icon={FileIcon} label={name} tag={false}>
      {/* Named main, as the Experiences page's column is, so the row and
          the editor lay out as they do there. */}
      <div className="@container/main flex flex-col gap-4">
        {SECTIONS.map((section) => {
          // Each entry keeps its place in the reading, which the editor's calls name.
          const found = entries
            .map((entry, index) => ({ entry, index }))
            .filter(({ entry }) => entry.section === section.id);
          if (!found.length) return null;
          const editable = editingGroup === section.id;
          return (
            <Card as="section" key={section.id} aria-label={section.label}>
              {heading(section.id, section.label)}
              <ul role="list" className="divide-border-subtle mt-2 flex flex-col divide-y">
                {found.map(({ entry, index }) => (
                  <li key={index} className="py-3">
                    {editing === index ? (
                      <EntryEditor
                        initial={draftOfPreview(entry)}
                        onSave={(draft) => {
                          onSaveEntry(index, previewOfDraft(draft, entry));
                          focusOn(editId(index));
                        }}
                        onCancel={() => {
                          onEditEntry(null);
                          focusOn(editId(index));
                        }}
                        onDelete={() => {
                          onLeaveOutEntry(index);
                          focusOn(doneId(section.id));
                        }}
                      />
                    ) : (
                      <EntryRow
                        entry={rowOfPreview(entry)}
                        open
                        actions={
                          editable &&
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
                          entry.replaces.length > 0 && (
                            // Inert, not a status colour: replacing is no stage and owes
                            // nothing (frontend/docs/design.md, colour meanings).
                            <div className="mt-1.5">
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
            </Card>
          );
        })}
        {skills.length > 0 && (
          <Card as="section" aria-label="Skills">
            {heading("skills", "Skills")}
            <ul className="mt-3 flex flex-wrap gap-2">
              {skills.map((skill) => (
                <li
                  key={skill.name}
                  className="rounded-control text-note text-ink border-border-subtle inline-flex items-center gap-1.5 border px-2 py-1"
                >
                  {skill.name}
                  {/* Its × in edit mode only, as on Experiences (KAN-363). */}
                  {editingGroup === "skills" && (
                    <IconButton
                      label={`Remove ${skill.name}`}
                      tooltip="Leave this skill out"
                      onClick={() => onRemoveSkill(skill.name)}
                    >
                      <XIcon aria-hidden className="size-3" />
                    </IconButton>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </Field>
  );
}
