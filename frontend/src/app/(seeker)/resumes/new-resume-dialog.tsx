"use client";

import { FileTextIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { UploadIcon } from "@/components/icons";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { matches, searchWords } from "@/components/resume-list";
import {
  PrimaryBadge,
  RESUME_TD,
  RESUME_TH,
  TargetJob,
  type GridCompany,
} from "@/components/resume-row";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/shadcn/table";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Missing } from "@/components/ui/missing";
import { OptionRow } from "@/components/ui/option-row";
import { OrDivider } from "@/components/ui/or-divider";
import { Radio } from "@/components/ui/radio-row";
import { SearchField } from "@/components/ui/search-field";
import { cn } from "@/lib/cn";
import type { BuiltResume } from "@/lib/built-resume-actions";
import type { ResumeItem } from "@/lib/resume-actions";

import { LocalDate } from "../local-time";
import { ResumeViewButton } from "../jobs/[jobId]/tailor/resume-preview";
import type { Source } from "../jobs/resume-picker";

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
 *   Start With a Resume You Have  a small Documents table (`StartTable`):
 *                                a radio per row, the name with the
 *                                Primary badge, Target Job, Date Modified
 *                                and View, always shown; then Start From
 *                                This Resume: a built resume copied, or one
 *                                upload's own entries as a new resume
 *                                (POST .../built-resumes/copy), opened in
 *                                the editor
 *
 * The first two are the shared option rows (components/ui/option-row.tsx,
 * Auto Apply's setup row), and act at once; the third needs a pick, so it
 * ends with the footer's filled button, as every resume picker does.
 *
 * The header and the footer stay put and the body scrolls between them
 * (2026-11-11): the whole dialog scrolled as one, and the footer's buttons
 * sat below the window. The third way was "Copy a Resume You Have", over
 * Tailor's picker cards (a star at the right end, the type's badge on
 * every card, View on hover) until then; the user wanted a table's few
 * columns, the badge by the name, and no type.
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
  /** Makes the new resume and opens it; its error, if any, shows here. */
  onCopy: (source: Source) => Promise<string | null>;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[min(52rem,calc(100dvh-2rem))] flex-col gap-0 overflow-hidden p-0 sm:max-w-4xl">
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

/** One resume to start from, as the table draws it. */
type StartRow = {
  key: string;
  name: string;
  primary: boolean;
  /** The Documents table's Date Modified: the last edit, else when made. */
  modified: string | null;
  /** A tailored resume's posting title. */
  role: string | null;
  company: GridCompany | null;
  source: Source;
};

/** Every resume, the primary first, then the newest. */
function rowsOf(built: BuiltResume[], uploaded: ResumeItem[]): StartRow[] {
  return [
    ...built.map((r) => ({
      key: `built:${r.id}`,
      name: r.name,
      primary: r.is_default,
      modified: r.edited_at ?? r.created_at,
      role: r.job_posting_id ? (r.posting_title ?? "A job posting") : null,
      company:
        r.job_posting_id && r.posting_company
          ? {
              name: r.posting_company,
              logoUrl: r.posting_logo_url,
              domain: r.posting_company_domain,
            }
          : null,
      source: { builtResumeId: r.id } as Source,
    })),
    ...uploaded
      .filter((r) => r.storage_path)
      .map((r) => ({
        key: `uploaded:${r.id}`,
        name: r.original_filename ?? "Uploaded resume",
        primary: r.is_default,
        modified: r.created_at,
        role: null,
        company: null,
        source: { uploadedResumeId: r.id } as Source,
      })),
  ].sort(
    (a, b) =>
      Number(b.primary) - Number(a.primary) ||
      Date.parse(b.modified ?? "0") - Date.parse(a.modified ?? "0"),
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
  onCopy: (source: Source) => Promise<string | null>;
}) {
  const rows = rowsOf(built, uploaded);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const words = searchWords(query);
  const shown = rows.filter((r) =>
    matches(`${r.name} ${r.role ?? ""} ${r.company?.name ?? ""}`, words),
  );
  const row = rows.find((r) => r.key === picked) ?? null;

  async function start() {
    if (!row) return;
    setBusy(true);
    setError(null);
    const failed = await onCopy(row.source);
    // On success the editor's page takes over; the dialog stays until then.
    if (failed) {
      setBusy(false);
      setError(failed);
    }
  }

  return (
    <>
      <DialogHeader className="border-border-subtle border-b px-6 pt-5 pr-12 pb-4">
        <DialogTitle className="text-subtitle font-semibold">Generate a Resume</DialogTitle>
        <DialogDescription>
          Start from your experiences, upload a resume, or start with one you already have.
        </DialogDescription>
      </DialogHeader>

      {/* overscroll-none: a fling past the end stops here, not on the page. */}
      <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-none px-6 py-5">
        <Card padding="none" className="divide-border-subtle shrink-0 divide-y overflow-hidden">
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

        <section aria-labelledby="start-with" className="flex min-w-0 flex-col gap-3">
          <div>
            <h3 id="start-with" className="text-body text-ink font-semibold">
              Start With a Resume You Have
            </h3>
            <p className="text-note text-ink-meta mt-0.5">
              A new resume starts as the one you pick prints, so you can change it and keep the
              original.
            </p>
          </div>
          {rows.length === 0 ? (
            <p className="text-note text-ink-meta py-2">
              You have no resumes yet. Start from your experiences or upload one.
            </p>
          ) : (
            <>
              <SearchField
                id="start-with-search"
                label="Search resumes"
                placeholder="Search by name or job"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              {shown.length === 0 ? (
                <p className="text-note text-ink-meta py-2">None of your resumes match.</p>
              ) : (
                <StartTable rows={shown} picked={picked} onPick={setPicked} />
              )}
            </>
          )}
        </section>
      </div>

      <div className="border-border-subtle flex flex-wrap items-center justify-end gap-3 border-t px-6 py-3">
        {error && (
          <p role="alert" className="text-note text-danger mr-auto">
            {error}
          </p>
        )}
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={() => void start()} disabled={!row || busy}>
          {busy ? "Starting…" : "Start From This Resume"}
        </Button>
      </div>
    </>
  );
}

/**
 * The resumes to start from as a small Documents table
 * (resumes/resume-list.tsx, components/resume-row.tsx): a radio, Name with
 * the Primary badge beside it, Target Job (a dash for none), Date Modified,
 * and View, always shown. No Type: the user found it took room a choice
 * did not need. A click anywhere on a row picks it; the radios are one
 * group, so the arrow keys move the pick. Below `@2xl` of the table Target
 * Job folds under the name, as the Documents table's does.
 */
function StartTable({
  rows,
  picked,
  onPick,
}: {
  rows: StartRow[];
  picked: string | null;
  onPick: (key: string) => void;
}) {
  return (
    <div className="border-border-subtle rounded-card @container overflow-hidden border">
      <Table aria-label="Your resumes" className="table-fixed">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-11 pr-0 pl-4">
              <span className="sr-only">Pick</span>
            </TableHead>
            <TableHead className={RESUME_TH}>Name</TableHead>
            <TableHead className={cn(RESUME_TH, "hidden w-64 @2xl:table-cell")}>
              Target Job
            </TableHead>
            <TableHead className={cn(RESUME_TH, "w-32")}>Date Modified</TableHead>
            <TableHead className="w-24">
              <span className="sr-only">View</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const on = row.key === picked;
            return (
              <TableRow
                key={row.key}
                onClick={() => onPick(row.key)}
                className={cn(
                  "h-14 cursor-pointer",
                  on ? "bg-brand-tint hover:bg-brand-tint" : "hover:bg-hover",
                )}
              >
                <TableCell className="pr-0 pl-4">
                  <Radio
                    name="start-with"
                    value={row.key}
                    checked={on}
                    onChange={() => onPick(row.key)}
                    aria-label={`Start with ${row.name}`}
                  />
                </TableCell>
                <TableCell className={cn(RESUME_TD, "overflow-hidden py-2")}>
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="text-label text-ink truncate font-medium" title={row.name}>
                      {row.name}
                    </span>
                    {row.primary && <PrimaryBadge />}
                  </div>
                  {row.role && (
                    <p className="text-ink-meta truncate @2xl:hidden">
                      {row.company ? `${row.role} at ${row.company.name}` : row.role}
                    </p>
                  )}
                </TableCell>
                <TableCell className={cn(RESUME_TD, "hidden @2xl:table-cell")}>
                  {row.role ? (
                    <TargetJob role={row.role} company={row.company} />
                  ) : (
                    <Missing word="No target job" />
                  )}
                </TableCell>
                <TableCell className={RESUME_TD}>
                  {row.modified && <LocalDate at={row.modified} />}
                </TableCell>
                {/* Its own click: View opens the resume, not a pick. */}
                <TableCell className="pr-2 pl-0 text-center" onClick={(e) => e.stopPropagation()}>
                  <ResumeViewButton name={row.name} resumeKey={row.key} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
