"use client";

import { FileArrowDownIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { BriefcaseIcon, FileIcon, PencilIcon, TrashIcon } from "@/components/icons";
import {
  PrimaryStar,
  ResumeCard,
  ROW_ACTION,
  ROW_WIDE,
  RowMoreMenu,
} from "@/components/resume-row";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { TextField } from "@/components/ui/text-field";
import {
  deleteBuiltResume,
  renameBuiltResume,
  setDefaultBuiltResume,
  type BuiltResume,
} from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

import { rememberReturnTo } from "../jobs/[jobId]/page-actions";
import { DeleteResumeConfirm } from "./delete-confirm";
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
 * day line names the job posting it was made for, a link to that posting's
 * page while the Jobs page lists it (a closed one's page is a 404). The whole card is
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
}: {
  resume: BuiltResume;
  reload: () => Promise<void>;
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

  return (
    <li>
      {renaming ? (
        <RenameForm
          id={resume.id}
          name={resume.name}
          saving={saving}
          onSave={rename}
          onCancel={() => setRenaming(false)}
        />
      ) : (
        <ResumeCard
          name={resume.name}
          href={`/resumes/${encodeURIComponent(resume.id)}`}
          about={
            resume.job_posting_id && resume.posting_title ? (
              <>
                <BriefcaseIcon className="size-3.5 shrink-0" />
                <span className="truncate">
                  For <PostingLink resume={resume} />
                </span>
              </>
            ) : (
              <>
                <FileIcon className="size-3.5 shrink-0" />
                <span className="truncate">Made from your experiences</span>
              </>
            )
          }
          // The resume still opens and downloads; only Tailor needs a live
          // posting.
          badge={resume.posting_closed && <Badge tone="inert">Posting Closed</Badge>}
          created={resume.created_at}
          edited={edited ? resume.edited_at : null}
          actions={
            <>
              <PrimaryStar
                name={resume.name}
                primary={resume.is_default}
                onMakePrimary={makePrimary}
              />
              <div className={ROW_WIDE}>
                <IconButton
                  label={`Rename ${resume.name}`}
                  tooltip="Rename"
                  className={ROW_ACTION}
                  onClick={() => setRenaming(true)}
                >
                  <PencilIcon className="size-4" />
                </IconButton>
                <IconButton
                  label={`Download ${resume.name} as a PDF`}
                  tooltip={downloadLabel}
                  className={ROW_ACTION}
                  disabled={download.busy !== null}
                  onClick={() => download.pick("pdf")}
                >
                  <FileArrowDownIcon aria-hidden className="size-4" />
                </IconButton>
                <DeleteResumeConfirm
                  onDelete={remove}
                  trigger={
                    <IconButton
                      label={`Delete ${resume.name}`}
                      tooltip="Delete"
                      className={cn(ROW_ACTION, "hover:text-danger")}
                    >
                      <TrashIcon className="size-4" />
                    </IconButton>
                  }
                />
              </div>
              <RowMoreMenu
                name={resume.name}
                onRename={() => setRenaming(true)}
                download={{
                  label: downloadLabel,
                  busy: download.busy !== null,
                  onPick: () => download.pick("pdf"),
                }}
                onDelete={remove}
              />
            </>
          }
        />
      )}
      <div className="mt-2 empty:hidden">
        <DownloadNotes download={download} />
      </div>
      {error && (
        <p role="alert" className="text-note text-danger mt-2">
          {error}
        </p>
      )}
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
 * The resume's name, open for typing (KAN-258): Rename turns the card into
 * this form, a built resume's or an upload's (KAN-268), as Edit opens a bank entry in place, with the bank's form
 * buttons at a field's height. A name left as it was closes the form with
 * no call; Escape or Cancel keeps the name.
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
          {saving ? "Saving…" : "Save Name"}
        </Button>
      </div>
    </form>
  );
}
