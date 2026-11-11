"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { BuiltPageTile, PostingLogoTile, ResumeCard } from "@/components/resume-row";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import {
  deleteBuiltResume,
  renameBuiltResume,
  setDefaultBuiltResume,
  type BuiltResume,
} from "@/lib/built-resume-actions";

import { rememberReturnTo } from "../jobs/[jobId]/page-actions";
import { ResumeThumbnail } from "../jobs/[jobId]/tailor/resume-preview";
import { DownloadNotes, useResumeDownload } from "./download-menu";

/**
 * One built resume, drawn as an uploaded one's card is (`ResumeCard`,
 * 2026-11-10): the file tile, the name and what it was made from or for,
 * Created and Last Edited in columns, then the star, Rename, Download PDF
 * and Delete: the same four icons as an upload's card. Preview (an eye,
 * KAN-358, Tailor's `ResumePreviewDialog`) came off on 2026-11-10, the
 * user's call: the card opens the resume anyway, and four icons on every
 * card read as one list.
 * Download PDF is the editor's PDF download (`useResumeDownload`: it keeps
 * nothing, with the missing-character warning under the row), on the card
 * since KAN-268. A tailored resume takes the star too since then, and its
 * second line names the job posting it was made for ("Software Engineer
 * Intern at Matic", with no "For", which the briefcase already says), a
 * link to that posting's page while the Jobs page lists it (a closed one's
 * page is a 404, so its line is plain text). It shows no Posting Closed
 * badge (2026-11-10, the user's call): the resume opens and downloads
 * either way, and only Tailor needs a live posting. The whole card is
 * one target: the name's link stretches over it (`after:inset-0`), the
 * icons sit above that, and the card lifts under the pointer as every
 * whole-target card does (`docs/motion.md`). Below `@xl` of the row,
 * Rename, Download PDF and Delete sit in its More menu (`RowMoreMenu`,
 * KAN-575); the star and Preview stay.
 */
export function BuiltResumeRow({
  resume,
  reload,
  onDelete,
  layout = "list",
}: {
  resume: BuiltResume;
  reload: () => Promise<void>;
  /** The Resumes tab's layout (KAN-766). */
  layout?: "list" | "grid";
  /** The list hides the row and sends the delete (KAN-388). */
  onDelete: (send: () => Promise<{ error: string | null }>) => void;
}) {
  const [renaming, setRenaming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const download = useResumeDownload(resume.id);

  async function makePrimary() {
    setError(null);
    const { error } = await setDefaultBuiltResume(resume.id);
    if (error) return setError(error);
    await reload();
  }

  // The form stays open until the list has the new name, so the old one
  // never flashes back.
  async function rename(name: string) {
    setSaving(true);
    setError(null);
    const { error } = await renameBuiltResume(resume.id, name);
    if (!error) await reload();
    setSaving(false);
    if (error) return setError(error);
    setRenaming(false);
  }

  // The row leaves the list at once, so the list runs the delete and
  // shows a failure (KAN-388).
  async function remove() {
    onDelete(() => deleteBuiltResume(resume.id));
  }

  // The API sends edited_at equal to created_at until the first change.
  const edited = Date.parse(resume.edited_at) > Date.parse(resume.created_at);
  const downloadLabel = download.busy === "pdf" ? "Making PDF…" : "Download PDF";

  const notes = (
    <>
      <div className="mt-2 empty:hidden">
        <DownloadNotes download={download} />
      </div>
      {error && (
        <p role="alert" className="text-note text-danger mt-2">
          {error}
        </p>
      )}
    </>
  );
  const card = (
    <ResumeCard
      layout={layout}
      type={resume.job_posting_id ? "tailored" : "generated"}
      company={
        resume.job_posting_id && resume.posting_company
          ? {
              name: resume.posting_company,
              logoUrl: resume.posting_logo_url,
              domain: resume.posting_company_domain,
            }
          : undefined
      }
      thumbnail={
        <ResumeThumbnail
          source={{ built_resume_id: resume.id }}
          version={resume.edited_at}
          fallback={<BuiltPageTile />}
        />
      }
      rename={renaming ? { saving, onSave: rename, onCancel: () => setRenaming(false) } : undefined}
      name={resume.name}
      href={`/resumes/${encodeURIComponent(resume.id)}`}
      tile={
        resume.job_posting_id ? (
          <PostingLogoTile
            company={resume.posting_company ?? resume.posting_title ?? resume.name}
            logoUrl={resume.posting_logo_url}
            domain={resume.posting_company_domain}
          />
        ) : (
          <BuiltPageTile />
        )
      }
      about={
        resume.job_posting_id && resume.posting_title ? <PostingLink resume={resume} /> : undefined
      }
      notes={layout === "list" ? notes : undefined}
      created={resume.created_at}
      edited={edited ? resume.edited_at : null}
      actions={{
        primary: resume.is_default,
        onMakePrimary: makePrimary,
        onRename: () => setRenaming(true),
        download: {
          label: downloadLabel,
          busy: download.busy !== null,
          onPick: () => download.pick("pdf"),
        },
        onDelete: remove,
      }}
    />
  );
  // A table row prints its notes under its name; a grid card under itself.
  return layout === "list" ? (
    card
  ) : (
    <li>
      {card}
      {notes}
    </li>
  );
}

/**
 * The job posting a tailored resume was made for. Above the card's
 * stretched link, so a press on it opens the posting, not the editor. The
 * click makes the posting page's Back return here (rememberReturnTo).
 */
function PostingLink({ resume }: { resume: BuiltResume }) {
  const label = resume.posting_company
    ? `${resume.posting_title} at ${resume.posting_company}`
    : resume.posting_title;
  if (resume.posting_closed || !resume.job_posting_id) return <>{label}</>;
  return (
    <Link
      href={`/jobs/${encodeURIComponent(resume.job_posting_id)}`}
      onClick={() => rememberReturnTo("/resumes")}
      className="text-brand hover:text-brand-hover relative z-10 underline-offset-2 hover:underline"
    >
      {label}
    </Link>
  );
}

/**
 * The resume's name, open for typing (KAN-258), on an upload's own page
 * (`uploaded/[id]/viewer.tsx`): a labeled field with Cancel and Save. The
 * Resumes page's cards rename in place instead (`RenamingCard`,
 * 2026-11-10). A name left as it was closes the form with no call; Escape
 * or Cancel keeps the name.
 */
export function RenameForm({
  id,
  name,
  saving,
  onSave,
  onCancel,
}: {
  id: string;
  name: string;
  saving: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState(name);
  const trimmed = draft.trim();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (trimmed === name) return onCancel();
    onSave(trimmed);
  }

  return (
    <form onSubmit={submit} className="mt-2 flex flex-wrap items-end gap-2">
      <div className="min-w-0 flex-1 basis-56">
        <TextField
          id={`resume-name-${id}`}
          label="Resume Name"
          required
          autoFocus
          maxLength={80}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") onCancel();
          }}
        />
      </div>
      <div className="flex gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !trimmed}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}
