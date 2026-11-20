"use client";

import { useId, useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { CloseIcon, FileIcon, PdfIcon, UploadIcon } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const MAX_SIZE = 5 * 1024 * 1024;

/** The file picker's filter, for a picker with no dropzone (the Resumes
 *  page's Upload Resume, KAN-362). */
export const RESUME_ACCEPT = ALLOWED_EXTENSIONS.join(",");

/** Why a picked file cannot be a resume, or null: the dropzone's checks,
 *  shared with Upload Resume so both say the same. */
export function resumeFileError(file: File): string | null {
  if (!ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) {
    return "Only PDF and DOCX files are accepted.";
  }
  if (file.size > MAX_SIZE) return "File must be under 5 MB.";
  return null;
}

type ResumeUploadProps = {
  file: File | null;
  onFileChange: (file: File) => void;
  onRemove: () => void;
  /** An upload is in flight. The dropzone says so, Browse Files is disabled
   *  and a second pick or drop is ignored until the parent clears it. */
  busy?: boolean;
};

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/**
 * The resume dropzone (onboarding's upload, the design kit), redrawn on
 * 2026-11-17 after a modern upload dialog the user chose: a white well with
 * a dashed edge, a file glyph wearing an upload badge, one line, "Drag and
 * drop your resume here or choose a file", and the formats and size limit
 * under the well, left and right, instead of a grey well with a third line
 * and an outlined Browse Files button inside it. The picked file is a row
 * of its own: the file's glyph on a white tile, its name and size, and a ×;
 * while it is read, a bar runs under it.
 *
 * THE WELL IS ONE BUTTON, so the keyboard and a screen reader reach the
 * picker from it; the formats line names it. It was a div whose click
 * opened the picker, reachable by keyboard only through Browse Files inside
 * it. The file input sits outside the well, so its own click cannot bubble
 * back into it.
 */
export function ResumeUpload({ file, onFileChange, onRemove, busy = false }: ResumeUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  // An error stays until the next valid file replaces it: one that clears
  // itself after a few seconds is gone before a slow reader reaches it.
  function handleFile(next: File) {
    if (busy) return;
    const error = resumeFileError(next);
    setFileError(error);
    if (!error) onFileChange(next);
  }

  function handleSelect(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0];
    if (next) handleFile(next);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    const next = event.dataTransfer.files?.[0];
    if (next) handleFile(next);
  }

  return (
    <div>
      <button
        type="button"
        aria-busy={busy}
        aria-describedby={hintId}
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false);
        }}
        onDrop={handleDrop}
        className={cn(
          "border-border-control bg-panel rounded-card hover:border-ink-meta hover:bg-well/50 focus-visible:ring-brand-ring flex w-full flex-col items-center border border-dashed px-6 py-12 transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none",
          dragging && "border-brand bg-brand-tint hover:border-brand hover:bg-brand-tint",
          busy && "cursor-progress opacity-60",
        )}
      >
        {/* A page with an upload badge on its corner. */}
        <span aria-hidden className="relative">
          <FileIcon className="text-ink-subtle size-12" />
          <span className="bg-brand text-on-brand ring-panel absolute -right-1.5 -bottom-1 grid size-6 place-items-center rounded-full ring-2">
            <UploadIcon className="size-3.5" />
          </span>
        </span>
        <span className="text-body text-ink mt-4">
          {busy ? (
            "Reading your resume…"
          ) : (
            <>
              <span className="pointer-coarse:hidden">Drag and drop your resume here or </span>
              <span className="text-brand-ink font-semibold underline underline-offset-2 pointer-coarse:no-underline">
                <span className="pointer-coarse:hidden">choose a file</span>
                <span className="hidden pointer-coarse:inline">Choose a file</span>
              </span>
            </>
          )}
        </span>
      </button>
      <input ref={inputRef} type="file" accept={RESUME_ACCEPT} onChange={handleSelect} hidden />

      <p id={hintId} className="text-note text-ink-meta mt-2 flex justify-between gap-4">
        <span>Supported formats: PDF, DOCX</span>
        <span>Maximum size: 5 MB</span>
      </p>

      {fileError && (
        <p role="alert" className="text-note text-danger mt-2">
          {fileError}
        </p>
      )}

      {file && (
        <div className="bg-well rounded-card mt-4 p-3">
          <div className="flex items-center gap-3">
            <span className="bg-panel ring-border-subtle rounded-control grid size-10 shrink-0 place-items-center ring-1">
              <PdfIcon className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body text-ink truncate font-medium">{file.name}</p>
              <p className="text-note text-ink-meta">
                {busy ? "Reading…" : formatBytes(file.size)}
              </p>
            </div>
            <IconButton
              place="row"
              tooltip={false}
              label="Remove resume"
              disabled={busy}
              onClick={onRemove}
            >
              <CloseIcon />
            </IconButton>
          </div>
          {/* While WorkIt reads it: a bar with no figure, since the API
              sends no progress. */}
          {busy && (
            <div className="bg-ink/8 mt-3 h-1.5 overflow-hidden rounded-full">
              <div className="bg-brand h-full w-full animate-pulse rounded-full" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
