"use client";

import { PdfIcon } from "@/components/icons";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";
import type { BuiltResume } from "@/lib/built-resume-actions";
import type { ResumeItem } from "@/lib/resume-actions";

import { ResumeFirstPage } from "../jobs/[jobId]/tailor/resume-preview";
import { LocalDate, LocalDateTime } from "../local-time";

/** What the Resumes page found a resume the student already has for: a
 *  Generate that would print the same as a built resume, or an upload whose
 *  text an upload already has. `resume` is that resume from the page's
 *  lists, for its card and first page; with none (the lists not yet read
 *  again), the modal names it alone. */
export type Duplicate =
  | { kind: "generate"; name: string; resume?: BuiltResume }
  | { kind: "upload"; name: string; resume?: ResumeItem };

/**
 * The modal for a resume the student already has (KAN-267), reworded as an
 * "Are you sure?" (KAN-444, the user's calls of 2026-11-10). It said only
 * the API's "Duplicate Resume found: <name>" with OK, which flagged the
 * copy but did not say what it meant or let the student go on.
 *
 * It opens before Generate's steps dialog: the button says "Checking…"
 * while the API compares, and only a check that passed, or a Confirm,
 * opens "Generating Your Resume". Under the sentence, the resume it matches
 * as a card (name and when it was created and edited) and its first page,
 * so the student sees which one it is.
 *
 * - **Generate**: "<name> has the same content." Confirm makes the copy
 *   anyway (`onConfirm`, Generate with `allow_duplicate`); Cancel makes
 *   nothing. A copy is cheap and edits on its own, so the student decides.
 * - **Upload**: "Your upload <name> has the same text." with OK. An
 *   upload stays refused: the database keeps one upload per text
 *   (`resumes_text_hash_key`), and a copy would take one of the 5 slots.
 *
 * Open while `duplicate` is set.
 */
export function DuplicateResumeDialog({
  duplicate,
  onConfirm,
  onClose,
}: {
  duplicate: Duplicate | null;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const generate = duplicate?.kind === "generate";
  return (
    <Dialog open={duplicate != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-subtitle font-semibold">
            You Already Have This Resume
          </DialogTitle>
          <DialogDescription>
            {generate
              ? `${duplicate.name} has the same content. Confirm to make a copy anyway.`
              : `Your upload ${duplicate?.name ?? ""} has the same text.`}
          </DialogDescription>
        </DialogHeader>
        {duplicate?.resume && <Match duplicate={duplicate} />}
        <DialogFooter>
          {generate ? (
            <>
              <DialogClose render={<Button variant="secondary">Cancel</Button>} />
              <Button onClick={onConfirm}>Confirm</Button>
            </>
          ) : (
            <DialogClose render={<Button>OK</Button>} />
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** The resume it matches: its card, as the list draws its name and dates,
 *  and its first page. Read-only: the modal's only actions are its own. */
function Match({ duplicate }: { duplicate: Duplicate }) {
  const card =
    duplicate.kind === "generate" && duplicate.resume
      ? {
          name: duplicate.resume.name,
          created: duplicate.resume.created_at,
          // The API sends edited_at equal to created_at until the first change
          edited:
            Date.parse(duplicate.resume.edited_at) > Date.parse(duplicate.resume.created_at)
              ? duplicate.resume.edited_at
              : null,
          source: { built_resume_id: duplicate.resume.id },
          version: duplicate.resume.edited_at,
        }
      : duplicate.kind === "upload" && duplicate.resume
        ? {
            name: duplicate.resume.original_filename ?? duplicate.name,
            created: duplicate.resume.created_at,
            edited: null,
            source: { uploaded_resume_id: duplicate.resume.id },
            version: undefined,
          }
        : null;
  if (!card) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="border-border-subtle bg-well rounded-control flex items-center gap-3 border p-2">
        <PdfIcon className="size-5 shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="text-label text-ink truncate">{card.name}</div>
          <div className="text-note text-ink-meta truncate">
            {duplicate.kind === "upload" ? "Uploaded" : "Created"}{" "}
            {card.created && <LocalDateTime at={card.created} />}
            {card.edited && (
              <>
                {" · Last edited "}
                <LocalDate at={card.edited} />
              </>
            )}
          </div>
        </div>
      </div>
      <ResumeFirstPage source={card.source} label={card.name} version={card.version} />
    </div>
  );
}
