"use client";

import { useRouter } from "next/navigation";
import { createContext, use, useRef, useState, type ReactNode } from "react";

import { RowMoreMenu } from "@/components/resume-row";
import { deleteBuiltResume, setDefaultBuiltResume } from "@/lib/built-resume-actions";
import { deleteResume, setPrimaryResume } from "@/lib/resume-actions";

/** A resume WorkIt built (the editor's) or an upload (its own page). */
export type ResumeKind = "built" | "uploaded";

/**
 * A resume page's title row, as its two ends reach each other (KAN-825):
 * the title (`ResumeTitle`, ./resume-title.tsx) at the left and the ⋯ menu
 * (`ResumeMenu`) at the right, with the save status and Download between
 * them. The title hands over how to open its rename field (`attach`), so
 * the menu's Rename opens it, and a failed Make Primary or Delete shows
 * under the title, where a failed rename does.
 */
type TitleRow = {
  attach: (open: (() => void) | null) => void;
  rename: () => void;
  /** The editor's tour (./walkthrough.tsx), which it hands over once it can
   *  run one, for the menu's Take the Tour; null on an upload's page. */
  attachTour: (start: (() => void) | null) => void;
  tour: (() => void) | null;
  error: string | null;
  setError: (error: string | null) => void;
};

export const TitleRowContext = createContext<TitleRow | null>(null);

/** Round a resume page's title row: the editor's page (./page.tsx) and an
 *  upload's (../uploaded/[id]/viewer.tsx). Tailor's review has none, so
 *  its title renames from its own click alone. */
export function TitleRowProvider({ children }: { children: ReactNode }) {
  const opener = useRef<(() => void) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<(() => void) | null>(null);
  const [actions] = useState(() => ({
    attach: (open: (() => void) | null) => {
      opener.current = open;
    },
    rename: () => opener.current?.(),
    attachTour: (start: (() => void) | null) => setTour(() => start),
  }));
  return (
    <TitleRowContext value={{ ...actions, tour, error, setError }}>{children}</TitleRowContext>
  );
}

/**
 * A resume page's ⋯ (More actions), at its title row's end (KAN-825): the
 * Resumes list's own menu (`RowMoreMenu`) with Rename, Make Primary (while
 * it is not the primary) and Delete, which asks first. Open and Download
 * stay out: the page is open, and Download is the row's filled button. The
 * two resume pages differed until then: an upload's had Make Primary,
 * Rename and Delete as bordered buttons, and the editor had none of them,
 * nor any sign of which resume is the primary.
 *
 * Make Primary and Rename clear the router's copies, which renders the page
 * again in their answer (`lib/resume-revalidate.ts`), so the title's badge
 * and this menu follow the API. Delete passes `leaving`: rendered again,
 * the page would read a resume that is gone before the push to Resumes.
 */
export function ResumeMenu({
  kind,
  resumeId,
  name,
  primary,
}: {
  kind: ResumeKind;
  resumeId: string;
  name: string;
  primary: boolean;
}) {
  const row = use(TitleRowContext);
  const router = useRouter();
  // A second press of Delete Resume while the first is on its way
  const deleting = useRef(false);
  const setError = (error: string | null) => row?.setError(error);

  async function makePrimary() {
    setError(null);
    const { error } =
      kind === "built" ? await setDefaultBuiltResume(resumeId) : await setPrimaryResume(resumeId);
    if (error) setError(error);
  }

  async function remove() {
    if (deleting.current) return;
    deleting.current = true;
    setError(null);
    const { error } =
      kind === "built"
        ? await deleteBuiltResume(resumeId, { leaving: true })
        : await deleteResume(resumeId, { leaving: true });
    if (!error) return router.push("/resumes");
    deleting.current = false;
    setError(error);
  }

  return (
    <RowMoreMenu
      always
      name={name}
      onRename={row?.rename}
      onMakePrimary={primary ? undefined : makePrimary}
      onTour={row?.tour ?? undefined}
      onDelete={remove}
    />
  );
}
