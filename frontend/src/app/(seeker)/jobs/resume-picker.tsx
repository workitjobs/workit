"use client";

import { EyeIcon, TagIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { FieldFacet, type FacetOption } from "@/components/field-facet";
import { UploadIcon } from "@/components/icons";
import {
  matches,
  RESUME_TYPES,
  ResumeScroll,
  searchWords,
  type ResumeType,
} from "@/components/resume-list";
import { PrimaryStar, RESUME_ROW, ROW_ACTION, TypeBadge } from "@/components/resume-row";
import { RESUME_ACCEPT, resumeFileError } from "@/components/resume-upload";
import { Skeleton } from "@/components/shadcn/skeleton";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Radio } from "@/components/ui/radio-row";
import { SearchField } from "@/components/ui/search-field";
import { cn } from "@/lib/cn";
import { listBuiltResumes } from "@/lib/built-resume-actions";
import { listResumes, replaceResume, uploadResume, type ResumeItem } from "@/lib/resume-actions";
import { MAX_UPLOADS } from "@/lib/resume-limits";

import { LocalDate } from "../local-time";

/**
 * The resume picker that "Did You Apply?" (./apply-button.tsx), Tailor's
 * Pick a Resume (./[jobId]/tailor/tailor-screen.tsx) and Up Next's Choose
 * a Resume (../auto-apply/resume-dialog.tsx) share: one job posting's
 * resume list and an upload with the Resumes page's rules (KAN-267), so
 * the three dialogs never drift apart on the limit, the replace step or a
 * duplicate. The Experiences view's Choose a Resume to Show
 * (../experiences/resume-bar.tsx, KAN-361) shows its list too, with no job
 * posting: it builds its own `Choice` rows from the bank's resumes.
 */

/** One resume the student can pick: a built resume (a base resume, or one
 *  tailored to a posting) or an uploaded resume. */
export type Choice = {
  key: string;
  label: string;
  /** Base is a generated resume; Tailored is one tailored to a posting. */
  type: "Base" | "Tailored" | "Uploaded";
  /** Tailored to the job posting this picker is for. */
  forThisJob: boolean;
  /** The posting a tailored resume was made for, "Title at Company". */
  tailoredFor: string | null;
  /** Last edited (built) or uploaded, for the card's line. */
  at: string | null;
  /** When a built resume was made: its line says "Made" until its first
   *  edit, as the Resumes page's card does. */
  madeAt: string | null;
  source: Source;
  isDefault: boolean;
};
export type Source = { builtResumeId: string } | { uploadedResumeId: string };

/** The resumes one job posting can take, and the uploads for the limit. */
export async function loadChoices(
  jobId: string,
): Promise<{ choices: Choice[]; uploads: ResumeItem[]; error: string | null }> {
  const [built, uploaded] = await Promise.all([listBuiltResumes(), listResumes()]);
  if (built.error || uploaded.error) {
    return { choices: [], uploads: [], error: built.error ?? uploaded.error };
  }
  const choices: Choice[] = [
    ...(built.data ?? [])
      // A resume tailored to another posting shows only as the primary
      // (KAN-268): the student starred it, so it is theirs to pick.
      .filter((r) => r.job_posting_id == null || r.job_posting_id === jobId || r.is_default)
      .map((r) => ({
        key: `built:${r.id}`,
        label: r.name,
        type: r.job_posting_id ? ("Tailored" as const) : ("Base" as const),
        forThisJob: r.job_posting_id === jobId,
        tailoredFor: r.job_posting_id
          ? [r.posting_title, r.posting_company].filter(Boolean).join(" at ") || "A job posting"
          : null,
        at: r.edited_at,
        madeAt: r.created_at,
        source: { builtResumeId: r.id },
        isDefault: r.is_default,
      })),
    ...uploaded.resumes
      .filter((r) => r.storage_path)
      .map((r) => ({
        key: `uploaded:${r.id}`,
        label: r.original_filename ?? "Uploaded resume",
        type: "Uploaded" as const,
        forThisJob: false,
        tailoredFor: null,
        at: r.created_at,
        madeAt: null,
        source: { uploadedResumeId: r.id },
        isDefault: r.is_default,
      })),
  ];
  return { choices, uploads: uploaded.resumes, error: null };
}

/** The pick a list starts on: the resume tailored to this job, else the
 *  default resume, else the first. */
export function firstChoice(choices: Choice[]): Choice | undefined {
  return choices.find((c) => c.forThisJob) ?? choices.find((c) => c.isDefault) ?? choices[0];
}

/** Each kind of choice's type, for its badge and the Type filter. */
const GROUP: Record<Choice["type"], ResumeType> = {
  Uploaded: "uploaded",
  Base: "generated",
  Tailored: "tailored",
};

/** The list's order: the resume tailored to this job, then the primary,
 *  then the newest. */
const order = (a: Choice, b: Choice) =>
  Number(b.forThisJob) - Number(a.forThisJob) ||
  Number(b.isDefault) - Number(a.isDefault) ||
  Date.parse(b.at ?? "0") - Date.parse(a.at ?? "0");

/** A pickable card: the Resumes page's card box (`RESUME_ROW`), tinted
 *  while it holds the pick. The Experiences view's All Experiences row draws
 *  itself with it too, since it sits in the same radio group. */
export function pickRowClasses(picked: boolean) {
  return cn(
    RESUME_ROW,
    "group cursor-pointer transition-colors duration-150",
    picked ? "border-brand bg-brand-tint" : "hover:border-ink-meta hover:bg-hover",
  );
}

/** The Type filter's options, in the Resumes page's order. */
const TYPES: FacetOption[] = [...RESUME_TYPES];

/** What a dialog that takes an upload hands the list (KAN-267's rules):
 *  the student's uploads, for the limit; `onUploaded` reads the list again
 *  and picks the new file (or, on a duplicate, the one it matched);
 *  `onBusyChange` says when a file is on its way or waiting to replace
 *  one, so the dialog holds its own button. */
export type PickerUpload = {
  uploads: ResumeItem[];
  onUploaded: (uploadedId: string) => Promise<void>;
  onBusyChange: (busy: boolean) => void;
};

/** Under a page's list: the card's 18px padding and 1px border. */
const CARD_FOOT = 19;

/**
 * The student's resumes as the Resumes page lists them (KAN-406): one row
 * with the search (names and the postings they were tailored for), the
 * Type filter and, in a dialog that takes one, Upload Resume, then one
 * flat list in one scroll five cards high (components/resume-list.tsx),
 * each card the Resumes page's box with a radio and the type's badge. The
 * list puts the likely pick first: the resume tailored to this job, then
 * the primary, then the newest. One radio group spans the list, so a
 * click on a card or the arrow keys move the pick. Below a 36rem row the
 * search takes its own line and the filter and the button share the
 * next, as two even halves.
 *
 * It drew Uploaded, Generated and Tailored groups, each card with a PDF
 * mark, until 2026-11-10: the Resumes page had gone flat with a type badge
 * per resume (KAN-766), and a picker that still grouped read as another
 * app. The Type filter finds one type.
 *
 * It has no Sort and no Generate Resume, which the Resumes page's row
 * has: a dialog holds a few resumes, the list already puts the likely
 * pick first, and a resume generated mid-dialog is not the file the
 * student sent. Did You Apply? and Tailor had an upload section under the
 * list ("Sent a Different Resume?", a dropzone) until KAN-406: it took
 * more room than the list, and the Resumes page's button had replaced its
 * own dropzone in KAN-362.
 *
 * It was a table with a Generated or Uploaded switch and Type, Tailored For
 * and Last Edited columns (KAN-360) until the Resumes page took the grouped
 * list (KAN-404): the two read as different apps, and the columns said what
 * a card's one line says. The search and the filter only filter what
 * shows: the pick stays put, so neither drops it.
 *
 * With `onPreview`, each card has a Preview button (an eye) that opens the
 * resume without picking it: Tailor's step 1 shows the resume in a dialog
 * (`jobs/[jobId]/tailor/resume-preview.tsx`). The other dialogs pass none.
 * The eye shows on a card's hover or focus, as the Resumes table's row
 * actions do, and always on a touch screen: an eye on every card was one
 * more mark per row to read past.
 */
export function ResumeLists({
  name,
  choices,
  empty,
  picked,
  onPick,
  onPreview,
  upload,
  fill = false,
}: {
  name: string;
  choices: Choice[];
  /** What the list says when the student has no resume at all. */
  empty: string;
  picked: string | null;
  onPick: (key: string) => void;
  /** Given, each card has a Preview button that calls it. */
  onPreview?: (choice: Choice) => void;
  /** Given, the row has Upload Resume. */
  upload?: PickerUpload;
  /** On a page, not in a dialog (Tailor's Pick a Resume): the list runs
   *  down to the page's foot, inside a card (`ResumeScroll`'s `fill`). */
  fill?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [types, setTypes] = useState<ResumeType[]>([]);
  // A new upload is picked, so nothing may hide it.
  const sending = useUploadButton(upload, () => {
    setQuery("");
    setTypes([]);
  });

  const words = searchWords(query);
  const shown = choices
    .filter(
      (c) =>
        (types.length === 0 || types.includes(GROUP[c.type])) &&
        matches(`${c.label} ${c.tailoredFor ?? ""}`, words),
    )
    .sort(order);

  return (
    <div className="@container flex min-w-0 flex-col gap-3">
      <div className="grid grid-cols-2 items-center gap-2 @xl:flex">
        <SearchField
          id={`${name}-search`}
          label="Search resumes"
          placeholder="Search by name or job"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="col-span-2 @xl:min-w-48 @xl:flex-1"
        />
        <FieldFacet
          label="Type"
          Icon={TagIcon}
          options={TYPES}
          values={types}
          onChange={(values) => setTypes(values as ResumeType[])}
          className={cn("min-w-36", !sending.button && "col-span-2 @xl:col-auto")}
        />
        {sending.button}
      </div>
      {sending.panel}
      {choices.length === 0 ? (
        <p className="text-note text-ink-meta py-2">{empty}</p>
      ) : shown.length === 0 ? (
        <p className="text-note text-ink-meta py-2">None of your resumes match these filters.</p>
      ) : (
        // Its own scroll, so the dialog's footer stays put under a long list,
        // or, on a page, so the search above it stays in view.
        <div className="border-border-subtle rounded-card bg-panel border">
          <ResumeScroll label="Your resumes" fill={fill} below={fill ? CARD_FOOT : 0}>
            {shown.map((c) => (
              <li key={c.key}>
                <PickCard
                  choice={c}
                  name={name}
                  picked={picked === c.key}
                  onPick={onPick}
                  onPreview={onPreview}
                />
              </li>
            ))}
          </ResumeScroll>
        </div>
      )}
    </div>
  );
}

/** `ResumeLists` while `loadChoices` runs (KAN-561): the row's search and
 *  Type filter, then the list's box with three cards, as bars. One skeleton for all three dialogs, in place of the line
 *  "Loading your resumes…" each drew. */
export function ResumeListsSkeleton() {
  return (
    <div role="status" className="flex min-w-0 flex-col gap-3">
      <span className="sr-only">Loading your resumes</span>
      <div aria-hidden="true" className="flex items-center gap-2">
        <Skeleton className="h-10 min-w-0 flex-1 rounded-full" />
        <Skeleton className="h-10 w-36 shrink-0 rounded-full" />
      </div>
      <div
        aria-hidden="true"
        className="border-border-subtle rounded-card bg-panel border px-3 pt-1 pb-3"
      >
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className={RESUME_ROW}>
            <Skeleton className="size-4 shrink-0 rounded-full" />
            <span className="flex min-w-0 flex-1 flex-col gap-1.5 py-0.5">
              <Skeleton className="h-3.5 w-48 max-w-full" />
              <Skeleton className="h-3 w-28 max-w-full" />
            </span>
            <Skeleton className="h-6 w-6 shrink-0 rounded-full @md:w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** One resume as a pickable card: a radio, the name and its line
 *  ("Uploaded Oct 21", "Last edited Oct 21 · For …"), the type's badge as
 *  the Resumes table draws it (in a column 7rem wide, so the stars line
 *  up; its icon alone below the card's `@md`), and the primary star. The
 *  name wraps, never truncates: two resumes tailored for one company
 *  differ only at the end of their names. */
function PickCard({
  choice: c,
  name,
  picked,
  onPick,
  onPreview,
}: {
  choice: Choice;
  name: string;
  picked: boolean;
  onPick: (key: string) => void;
  onPreview?: (choice: Choice) => void;
}) {
  const edited = c.madeAt != null && c.at != null && Date.parse(c.at) > Date.parse(c.madeAt);
  const day = c.type === "Uploaded" || edited ? c.at : c.madeAt;
  return (
    <label className={pickRowClasses(picked)}>
      <Radio name={name} value={c.key} checked={picked} onChange={() => onPick(c.key)} />
      <span className="min-w-0 flex-1">
        <span className="text-label text-ink block break-words">{c.label}</span>
        <span className="text-note text-ink-meta block break-words">
          {c.type === "Uploaded" ? "Uploaded" : edited ? "Last edited" : "Made"}
          {day && (
            <>
              {" "}
              <LocalDate at={day} />
            </>
          )}
          {c.tailoredFor && (
            <>
              {" · For "}
              {c.forThisJob ? <ThisJob /> : c.tailoredFor}
            </>
          )}
        </span>
      </span>
      <span className="flex shrink-0 @md:w-28">
        <TypeBadge type={GROUP[c.type]} wordClassName="sr-only @md:not-sr-only" />
      </span>
      <PrimaryStar name={c.label} primary={c.isDefault} />
      {onPreview && (
        // Inside the card's label, so the click must not reach the radio:
        // a preview never moves the pick.
        <IconButton
          label={`Preview ${c.label}`}
          tooltip="Preview"
          className={cn(
            ROW_ACTION,
            "relative z-10 shrink-0 opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 pointer-coarse:opacity-100",
          )}
          onClick={(event) => {
            event.preventDefault();
            onPreview(c);
          }}
        >
          <EyeIcon aria-hidden className="size-4" />
        </IconButton>
      )}
    </label>
  );
}

/** The posting this picker is for, in place of its own title. Words, not
 *  a badge: a badge's tint vanished on the picked card's. */
function ThisJob() {
  return <span className="text-brand font-medium">This Job</span>;
}

/**
 * Upload Resume in a dialog's list row, the Resumes page's way (KAN-267):
 * under the limit the picked file uploads at once; at the limit it waits
 * under the row (`panel`) until the student picks an upload to replace
 * (Import Updated Resume: the old file's sent resumes keep a frozen copy),
 * since a dialog cannot send them to Resumes to delete one. `onSent` runs
 * once the list has the new file, so the list can clear what would hide
 * it. With no `upload`, the row has no button.
 */
function useUploadButton(upload: PickerUpload | undefined, onSent: () => void) {
  const [waiting, setWaiting] = useState<File | null>(null);
  const [replacing, setReplacing] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const busy = uploading || waiting != null;
  const onBusyChange = upload?.onBusyChange;
  useEffect(() => onBusyChange?.(busy), [busy, onBusyChange]);

  if (!upload) return { button: null, panel: null };
  const { uploads, onUploaded } = upload;

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setNote(null);
    const invalid = resumeFileError(file);
    if (invalid) return setError(invalid);
    if (uploads.length >= MAX_UPLOADS) {
      setWaiting(file);
      setReplacing(uploads[0]?.id ?? null);
      return;
    }
    void send(file, null);
  }

  async function send(file: File, replace: string | null) {
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    const { resume, error, duplicateOf } = replace
      ? await replaceResume(replace, fd)
      : await uploadResume(fd);
    if (!resume && !duplicateOf) {
      setUploading(false);
      return setError(error ?? "Could not upload the resume.");
    }
    await onUploaded((resume?.id ?? duplicateOf) as string);
    onSent();
    setUploading(false);
    setWaiting(null);
    setNote(
      duplicateOf
        ? `${error} It is picked under Uploaded.`
        : `Uploaded ${file.name}. It is picked under Uploaded.`,
    );
  }

  const button = (
    <>
      <Button
        variant="secondary"
        size="sm"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="@xl:ml-auto"
      >
        <UploadIcon className="size-4" /> {uploading ? "Reading Resume…" : "Upload Resume"}
      </Button>
      <input ref={inputRef} type="file" accept={RESUME_ACCEPT} onChange={pickFile} hidden />
    </>
  );

  const panel = (waiting || error || note) && (
    <div className="flex flex-col gap-2">
      {waiting && (
        // At the limit: which upload the new file replaces.
        <>
          <p className="text-note text-ink-muted">
            You have {MAX_UPLOADS} uploaded resumes, the most WorkIt keeps. Pick the one{" "}
            {waiting.name} replaces. Applications sent with it keep a copy.
          </p>
          <ResumeChoices
            legend="Upload to Replace"
            hideLegend
            name="replace"
            choices={uploads.map((r) => ({
              key: r.id,
              label: r.original_filename ?? "Uploaded resume",
            }))}
            picked={replacing}
            onPick={setReplacing}
          />
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setWaiting(null)}
              disabled={uploading}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => void send(waiting, replacing)}
              disabled={uploading || replacing == null}
            >
              {uploading ? "Reading Resume…" : "Replace It"}
            </Button>
          </div>
        </>
      )}
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
      {note && (
        <p className="text-note text-ink-muted" aria-live="polite">
          {note}
        </p>
      )}
    </div>
  );

  return { button, panel };
}

/** One radio row per resume, by its name. */
export function ResumeChoices({
  legend,
  hideLegend = false,
  name,
  choices,
  empty,
  picked,
  onPick,
}: {
  legend: string;
  hideLegend?: boolean;
  name: string;
  /** What an empty section says, under its title. */
  empty?: string;
  choices: { key: string; label: string }[];
  picked: string | null;
  onPick: (key: string) => void;
}) {
  // min-w-0: a fieldset's minimum width is its content's, so in the
  // dialog's two columns a long resume name pushed Generated Resumes over
  // Uploaded Resumes instead of wrapping.
  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className={hideLegend ? "sr-only" : "text-label text-ink mb-1"}>{legend}</legend>
      {choices.length === 0 && empty && <p className="text-note text-ink-meta">{empty}</p>}
      {choices.map((c) => (
        // Drawn as the list's cards are (`pickRowClasses`), siblings of theirs.
        <label key={c.key} className={cn(pickRowClasses(picked === c.key), "mt-0")}>
          <Radio
            name={name}
            value={c.key}
            checked={picked === c.key}
            onChange={() => onPick(c.key)}
          />
          {/* The name alone: the section title already says what kind it is,
              and a grey kind line under each name only repeated it. It
              wraps, never truncates: two resumes tailored for one company
              differ only at the end of their names. */}
          <span className="text-label text-ink min-w-0 break-words">{c.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
