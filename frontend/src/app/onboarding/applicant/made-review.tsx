"use client";

import { useEffect, useState, type MouseEvent } from "react";

import { ResumePreviewPane } from "@/app/(seeker)/jobs/[jobId]/tailor/resume-preview";
import { Editor, EditorSkeleton } from "@/app/(seeker)/resumes/[resumeId]/editor";
import { TitleRowProvider } from "@/app/(seeker)/resumes/[resumeId]/resume-menu";
import { ResumeTitle } from "@/app/(seeker)/resumes/[resumeId]/resume-title";
import { LoadFailed } from "@/components/ui/load-failed";
import { getBank, type Bank } from "@/lib/bank-actions";
import {
  getChoices,
  listBuiltResumes,
  renderResumePdf,
  type Choices,
} from "@/lib/built-resume-actions";
import { getProfile } from "@/lib/profile-actions";
import type { TailorSource } from "@/lib/tailor-actions";

/**
 * The resume step once its resume exists (2026-11-17): the resume itself,
 * inside onboarding, where the student sees it made and can change it
 * before the last two questions. A built resume opens in the real editor
 * (every line, Format, Fit to One Page, Download), as its own page draws
 * it; an upload shows its file, read-only, since an upload is edited by
 * uploading it again. The wizard draws the logo, the question and the
 * footer around it, whose Continue goes on to Authorization, so the student
 * never leaves onboarding for the app: onboarding first opened the editor's
 * own page, in the app's shell, which read as if setup were over.
 *
 * The editor's data is read here with the same actions its page reads on the
 * server, since the wizard is one client page. Its phone layout covers the
 * screen, so its back arrow is the way on (`onContinue`).
 */
export function MadeReview({
  made,
  tour = false,
  onTourEnd,
  onContinue,
}: {
  made: TailorSource;
  /** Start the editor's tour on a built resume (2026-11-17). */
  tour?: boolean;
  onTourEnd?: () => void;
  onContinue: () => void;
}) {
  if ("uploaded_resume_id" in made) {
    return (
      <div className="flex h-[min(72svh,64rem)] flex-col">
        <ResumePreviewPane source={made} label="Your resume" />
      </div>
    );
  }
  return (
    <BuiltReview
      resumeId={made.built_resume_id}
      tour={tour}
      onTourEnd={onTourEnd}
      onContinue={onContinue}
    />
  );
}

type Loaded = {
  initial: ReturnType<typeof renderResumePdf>;
  bank: Bank;
  choices: Choices;
  header: NonNullable<Awaited<ReturnType<typeof getProfile>>["profile"]>;
  name: string;
};

function BuiltReview({
  resumeId,
  tour,
  onTourEnd,
  onContinue,
}: {
  resumeId: string;
  tour: boolean;
  onTourEnd?: () => void;
  onContinue: () => void;
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [failed, setFailed] = useState(false);
  const [tries, setTries] = useState(0);

  useEffect(() => {
    let stale = false;
    // The first render starts at once, beside the reads, as the editor's
    // page starts it before its awaits.
    const initial = renderResumePdf(resumeId);
    Promise.all([getBank(resumeId), getChoices(resumeId), getProfile(), listBuiltResumes()])
      .then(([bank, choices, { profile }, resumes]) => {
        if (stale) return;
        if (!bank.data || !choices.data || !profile) return setFailed(true);
        setLoaded({
          initial,
          bank: bank.data,
          choices: choices.data,
          header: profile,
          name: resumes.data?.find((r) => r.id === resumeId)?.name ?? "Your Resume",
        });
      })
      .catch(() => !stale && setFailed(true));
    return () => {
      stale = true;
    };
  }, [resumeId, tries]);

  if (failed)
    return (
      <LoadFailed
        title="Your Resume Isn't Loading Right Now"
        onRetry={() => {
          setFailed(false);
          setTries((n) => n + 1);
        }}
      >
        It is saved, and you can open it later in Documents.
      </LoadFailed>
    );
  if (!loaded) return <EditorSkeleton />;
  return (
    // The editor sizes itself off the seeker pages' container (`@3xl/main`).
    <div className="@container/main">
      <TitleRowProvider>
        <Editor
          resumeId={resumeId}
          initial={loaded.initial}
          initialBank={loaded.bank}
          initialChoices={loaded.choices}
          initialHeader={loaded.header}
          heading={<ResumeTitle as="h2" resumeId={resumeId} name={loaded.name} />}
          // The phone's tip in the tour's place: the phone editor is
          // another layout, and the tour is drawn from 64rem only
          phoneBar={
            <p className="text-note text-ink-muted">
              Open the panel (the last button above) to add your school, jobs and skills.
            </p>
          }
          tour={tour}
          onTourEnd={onTourEnd}
          phoneBack={{
            href: "/onboarding/applicant?step=authorization",
            label: "Continue Setup",
            onClick: (event: MouseEvent) => {
              event.preventDefault();
              onContinue();
            },
          }}
        />
      </TitleRowProvider>
    </div>
  );
}
