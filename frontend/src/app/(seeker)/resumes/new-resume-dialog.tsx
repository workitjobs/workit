"use client";

import { FileTextIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { UploadIcon } from "@/components/icons";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { OptionRow } from "@/components/ui/option-row";
import { OrDivider } from "@/components/ui/or-divider";
import type { BuiltResume } from "@/lib/built-resume-actions";
import type { ResumeItem } from "@/lib/resume-actions";
import type { TailorSource } from "@/lib/tailor-actions";

import { ResumePreviewDialog } from "../jobs/[jobId]/tailor/resume-preview";
import { ResumeLists, toChoices, type Choice } from "../jobs/resume-picker";

/**
 * Generate Resume's dialog on the Resumes page (2026-11-11, after
 * Simplify's "How would you like to create this resume?"): the three ways
 * to start a resume in one place. Upload Resume was its own button beside
 * Generate Resume until then; the user wanted one button, named for the
 * main way.
 *
 *   Start From Your Experiences  Generate as it was: every bank entry, the
 *                                duplicate check, then the editor
 *                                (./built-resumes.tsx, `generate`)
 *   Upload a Resume              the page's file picker (./upload-resume.tsx,
 *                                `pick`); its experiences join the bank
 *   Copy a Resume You Have       Tailor's resume picker (../jobs/resume-
 *                                picker.tsx, `ResumeLists`: search, Type,
 *                                a radio per card, View), then Copy This
 *                                Resume: a built resume copied, or one
 *                                upload's own entries as a new resume
 *                                (POST .../built-resumes/copy), opened in
 *                                the editor
 *
 * The first two are the shared option rows (components/ui/option-row.tsx,
 * Auto Apply's setup row), and act at once; the copy needs a pick, so it
 * ends with the footer's filled button, as every resume picker does.
 */
export function NewResumeDialog({
  open,
  onOpenChange,
  built,
  uploaded,
  onGenerate,
  onUpload,
  uploadDisabled,
  onCopy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  built: BuiltResume[];
  uploaded: ResumeItem[];
  onGenerate: () => void;
  /** Opens the file picker. Called in the click, as a browser requires. */
  onUpload: () => void;
  /** Why Upload is off (the five-upload limit), or null. */
  uploadDisabled: string | null;
  /** Makes the copy and opens it; its error, if any, shows here. */
  onCopy: (choice: Choice) => Promise<string | null>;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        {open && (
          <Body
            built={built}
            uploaded={uploaded}
            onClose={() => onOpenChange(false)}
            onGenerate={onGenerate}
            onUpload={onUpload}
            uploadDisabled={uploadDisabled}
            onCopy={onCopy}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function Body({
  built,
  uploaded,
  onClose,
  onGenerate,
  onUpload,
  uploadDisabled,
  onCopy,
}: {
  built: BuiltResume[];
  uploaded: ResumeItem[];
  onClose: () => void;
  onGenerate: () => void;
  onUpload: () => void;
  uploadDisabled: string | null;
  onCopy: (choice: Choice) => Promise<string | null>;
}) {
  const choices = toChoices(built, uploaded);
  const [picked, setPicked] = useState<string | null>(null);
  const [preview, setPreview] = useState<Choice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const choice = choices.find((c) => c.key === picked) ?? null;

  async function copy() {
    if (!choice) return;
    setBusy(true);
    setError(null);
    const failed = await onCopy(choice);
    // On success the editor's page takes over; the dialog stays until then.
    if (failed) {
      setBusy(false);
      setError(failed);
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle className="text-subtitle font-semibold">Generate a Resume</DialogTitle>
        <DialogDescription>
          Start from your experiences, upload a resume, or copy one you already have.
        </DialogDescription>
      </DialogHeader>

      <Card padding="none" className="divide-border-subtle divide-y overflow-hidden">
        <OptionRow
          icon={<FileTextIcon aria-hidden className="text-ink size-5" />}
          title="Start From Your Experiences"
          line="Every experience in your bank, ready to edit."
          onClick={() => {
            onClose();
            onGenerate();
          }}
        />
        <OptionRow
          icon={<UploadIcon className="text-ink size-5" />}
          title="Upload a Resume"
          line={uploadDisabled ?? "A PDF or Word file. Its experiences join your bank."}
          disabled={uploadDisabled != null}
          onClick={() => {
            onUpload();
            onClose();
          }}
        />
      </Card>

      <OrDivider />

      <section aria-labelledby="copy-a-resume" className="flex min-w-0 flex-col gap-3">
        <div>
          <h3 id="copy-a-resume" className="text-body text-ink font-semibold">
            Copy a Resume You Have
          </h3>
          <p className="text-note text-ink-meta mt-0.5">
            A new resume starts as the one you pick prints, so you can change it and keep the
            original.
          </p>
        </div>
        <ResumeLists
          name="copy-from"
          choices={choices}
          empty="You have no resumes yet. Start from your experiences or upload one."
          picked={picked}
          onPick={setPicked}
          onPreview={setPreview}
        />
      </section>

      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
      <DialogFooter>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={() => void copy()} disabled={!choice || busy}>
          {busy ? "Copying…" : "Copy This Resume"}
        </Button>
      </DialogFooter>

      {preview && (
        <ResumePreviewDialog
          open
          onOpenChange={(open) => !open && setPreview(null)}
          label={preview.label}
          source={tailorSource(preview)}
        />
      )}
    </>
  );
}

/** The picker's source as the preview names it. */
export function tailorSource(choice: Choice): TailorSource {
  return "builtResumeId" in choice.source
    ? { built_resume_id: choice.source.builtResumeId }
    : { uploaded_resume_id: choice.source.uploadedResumeId };
}
