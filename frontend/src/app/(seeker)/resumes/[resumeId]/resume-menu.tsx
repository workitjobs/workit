"use client";

import { TrashIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { createContext, use, useRef, useState, type ReactNode } from "react";

import { IconButton } from "@/components/ui/icon-button";
import { deleteResume } from "@/lib/resume-actions";
import { cn } from "@/lib/cn";

import { DeleteResumeConfirm } from "../delete-confirm";

/** A resume WorkIt built (the editor's) or an upload (its own page). */
export type ResumeKind = "built" | "uploaded";

/**
 * A resume page's title row, as its parts reach the line under the title
 * (KAN-825): a failed rename, Make Primary (the star, `ResumeTitle`) or
 * Delete (`ResumeDelete`) shows there.
 */
type TitleRow = {
  error: string | null;
  setError: (error: string | null) => void;
};

export const TitleRowContext = createContext<TitleRow | null>(null);

/** Round a resume page's title row: the editor's page (./page.tsx) and an
 *  upload's (../uploaded/[id]/viewer.tsx). Tailor's review has none, so its
 *  title shows its own failures. */
export function TitleRowProvider({ children }: { children: ReactNode }) {
  const [error, setError] = useState<string | null>(null);
  return <TitleRowContext value={{ error, setError }}>{children}</TitleRowContext>;
}

/**
 * An upload's Delete, at its title row's end (2026-11-19): the trash, which
 * asks first, as the Resumes list's does, and returns to Resumes.
 *
 * The two resume pages had a ⋯ (KAN-825) with Rename, Make Primary, Take the
 * Tour and Delete. After Google Docs and Drive, the editor is the document
 * and the Resumes list the drive: the title renames in place and the star
 * beside it makes the resume the primary (`ResumeTitle`), the toolbar's ?
 * takes the tour, and a resume is deleted from the list, never mid edit. An
 * upload's page is a file's preview, as Drive's is, so it keeps Delete, and
 * with nothing else left in the menu, the menu went.
 *
 * Delete passes `leaving`: rendered again, the page would read a resume
 * that is gone before the push to Resumes.
 */
export function ResumeDelete({ resumeId, name }: { resumeId: string; name: string }) {
  const row = use(TitleRowContext);
  const router = useRouter();
  // A second press of Delete Resume while the first is on its way
  const deleting = useRef(false);

  async function remove() {
    if (deleting.current) return;
    deleting.current = true;
    row?.setError(null);
    const { error } = await deleteResume(resumeId, { leaving: true });
    if (!error) return router.push("/resumes");
    deleting.current = false;
    row?.setError(error);
  }

  return (
    <DeleteResumeConfirm
      onDelete={remove}
      trigger={
        <IconButton
          place="row"
          label={`Delete ${name}`}
          tooltip="Delete"
          className={cn("hover:text-danger")}
        >
          <TrashIcon />
        </IconButton>
      }
    />
  );
}
