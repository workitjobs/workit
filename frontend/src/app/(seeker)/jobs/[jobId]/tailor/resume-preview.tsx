"use client";

import { EyeIcon, FileArrowDownIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";
import { getResumeFileUrl } from "@/lib/resume-actions";
import { openDownload } from "@/lib/save-file";
import type { TailorSource } from "@/lib/tailor-actions";

import { loadPdfjs, PageSkeleton, PdfPages } from "../../../resumes/[resumeId]/pdf-pages";
import { THUMBNAIL_RATIO } from "../../../resumes/view";

/**
 * A resume shown read-only: in a dialog for Tailor's step 1, which opens
 * it from a card's Preview button (`onPreview` on `ResumeLists`), so the
 * student sees what they are about to tailor without picking it; and
 * inline on the review step, where the toolbar's View Original sets the
 * source resume beside the tailored one (`OriginalResume`). It draws with
 * the editor's `PdfPages` and no click targets, as an upload's own page
 * does. A DOCX cannot be drawn by pdf.js, so it gets a note and Download,
 * as its own page does.
 *
 * The PDF comes from /api/resume-preview (a built resume rendered, an
 * upload's file read), a route handler so a slow render never queues the
 * screen's server actions behind it. A built resume renders as it is now.
 *
 * Each answer is kept by its source for the page's life (`answered`), so a
 * resume shows only its own answer, however late an older one arrives, and
 * a resume opened again shows at once. A caller that knows when the
 * resume last changed passes it as `version` (the Resumes page's duplicate
 * modal, KAN-444), so an answer from before an edit is not shown after it. A failed one says so in a line, with
 * Try Again. Step 1 held the preview as a column beside the list until the
 * list needed the width; a dialog also gives the page room to be read.
 */

type Preview = { pdf: string | null; error: string | null };

const keyOf = (source: TailorSource) =>
  "built_resume_id" in source
    ? `built=${encodeURIComponent(source.built_resume_id)}`
    : `uploaded=${encodeURIComponent(source.uploaded_resume_id)}`;

/** Answers that drew, kept across the dialog's and the pane's mounts. */
const answered = new Map<string, Preview>();

/** Previews asked for at once: two (KAN-766). The Resumes grid asks for one
 *  per card that comes into view, and each built resume's is a PDF render
 *  on the API's small containers, so a grid of twenty asked for twenty
 *  renders together. The rest wait their turn. */
const AT_ONCE = 2;
let running = 0;
const waiting: (() => void)[] = [];

async function inTurn<T>(work: () => Promise<T>): Promise<T> {
  if (running >= AT_ONCE) await new Promise<void>((go) => waiting.push(go));
  running += 1;
  try {
    return await work();
  } finally {
    running -= 1;
    waiting.shift()?.();
  }
}

/** The source's preview, asked for once `enabled`, and a retry for a
 *  failed one. */
function useResumePreview(source: TailorSource, enabled: boolean, version?: string) {
  const [previews, setPreviews] = useState<Record<string, Preview>>({});
  // Sources asked for and not yet answered, so one opened away and back
  // is not asked for twice.
  const asking = useRef(new Set<string>());
  const query = keyOf(source);
  const key = version ? `${query}@${version}` : query;
  const preview = previews[key] ?? answered.get(key);
  const have = preview !== undefined;

  useEffect(() => {
    if (!enabled || have || asking.current.has(key)) return;
    asking.current.add(key);
    // pdf.js downloads while the server draws the PDF, as in the editor.
    loadPdfjs().catch(() => {});
    const keep = (answer: Preview) => {
      asking.current.delete(key);
      if (!answer.error) answered.set(key, answer);
      setPreviews((all) => ({ ...all, [key]: answer }));
    };
    inTurn(() => fetch(`/api/resume-preview?${query}`))
      .then(async (res) => {
        const body = (await res.json()) as Partial<Preview>;
        keep({
          pdf: body.pdf ?? null,
          error: res.ok ? null : (body.error ?? "The preview failed."),
        });
      })
      .catch(() => keep({ pdf: null, error: "Could not reach the server." }));
  }, [enabled, key, query, have]);

  function retry() {
    answered.delete(key);
    setPreviews((all) => {
      const rest = { ...all };
      delete rest[key];
      return rest;
    });
  }

  return { key, preview, retry };
}

/** The preview's pages, or its skeleton, its failure or a DOCX's note. */
function PreviewPages({
  source,
  label,
  enabled,
  version,
}: {
  source: TailorSource;
  label: string;
  enabled: boolean;
  version?: string;
}) {
  const { key, preview, retry } = useResumePreview(source, enabled, version);
  if (!preview) return <PageSkeleton />;
  if (preview.error) {
    return (
      <p role="alert" className="text-body text-danger">
        The preview could not be shown.{" "}
        <Button variant="link" onClick={retry}>
          Try Again
        </Button>
      </p>
    );
  }
  if (preview.pdf) {
    // Keyed by the source: PdfPages keeps its old document on screen until
    // a new one is read, which would show the last resume.
    return (
      <PdfPages
        key={key}
        pdf={preview.pdf}
        boxes={[]}
        selected={null}
        onSelect={() => {}}
        placeholder={<PageSkeleton />}
      />
    );
  }
  return "uploaded_resume_id" in source ? (
    <DocxNote id={source.uploaded_resume_id} label={label} />
  ) : null;
}

export function ResumePreviewDialog({
  open,
  onOpenChange,
  label,
  source,
  version,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The resume's name, the dialog's title. */
  label: string;
  source: TailorSource;
  /** When the resume last changed; a new one asks for the PDF again. */
  version?: string;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* Tall, so a page reads at once; its pages scroll under the title. */}
      <DialogContent className="flex h-[92vh] w-[92vw] max-w-none flex-col sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-subtitle pr-8 font-semibold break-words">
            {label}
          </DialogTitle>
          <DialogDescription className="sr-only">A preview of this resume.</DialogDescription>
        </DialogHeader>
        <ResumePreviewPane source={source} label={label} enabled={open} version={version} />
      </DialogContent>
    </Dialog>
  );
}

/** The preview's pages in their grey well, scrolling under whatever sits
 *  above it: the preview dialog's body, and Generate Resume's dialog when
 *  its View turns the dialog into the resume (resumes/new-resume-dialog.tsx)
 *  rather than opening this dialog over it. */
export function ResumePreviewPane({
  source,
  label,
  enabled = true,
  version,
}: {
  source: TailorSource;
  label: string;
  enabled?: boolean;
  version?: string;
}) {
  return (
    <div className="bg-well rounded-card min-h-0 flex-1 overflow-y-auto overscroll-none p-3 sm:p-4">
      <PreviewPages source={source} label={label} enabled={enabled} version={version} />
    </div>
  );
}

/**
 * The resume Tailor started from, read-only, beside the tailored one on
 * the review step (the title row's Original). The record keeps the
 * source's id, not its name, so it is labelled for what it is. Its label
 * is a bar the toolbar's shape and height (44px), level with it, so the
 * two pages start level and the pair reads as two of a kind: a history
 * glyph in brand, "Original Resume" in ink, and a Read Only tag, since
 * nothing on it can be clicked. It was a grey line of label type, which
 * the user found too quiet.
 */
export function OriginalResume({ source }: { source: TailorSource }) {
  return <PreviewPages source={source} label="Original Resume" enabled />;
}

/**
 * A resume's first page, small and read-only, for the Resumes page's
 * duplicate modal (KAN-444): "Resume #6 has the same content" was abstract,
 * and the page shows which resume it is before the student confirms a copy.
 * The frame is one Letter page tall, so only page 1 shows, and it costs one
 * render (about half a second) the first time a resume is shown.
 */
export function ResumeFirstPage({
  source,
  label,
  version,
}: {
  source: TailorSource;
  label: string;
  version?: string;
}) {
  return (
    <div
      aria-label={`First page of ${label}`}
      role="figure"
      className="border-border-subtle mx-auto w-56 overflow-hidden rounded-xs border shadow-sm"
      style={{ aspectRatio: "8.5 / 11" }}
    >
      <PreviewPages source={source} label={label} enabled version={version} />
    </div>
  );
}

/**
 * A resume's first page as a grid card's picture (KAN-766): the card's full
 * width and the top of the page (`THUMBNAIL_RATIO`, its name, contact line
 * and first section), drawn whole at the page's own shape and cut at the
 * box's foot, asked for only once the card is near the
 * screen (`useNear`) and then in turn (`inTurn`), and kept for the visit.
 * The whole page took 83% of a card and 1.5 rows of cards filled a laptop
 * screen; resumes from one bank look alike below their first section
 * anyway (2026-11-10).
 * Read-only and deaf to the pointer, so a press opens the card. A file
 * pdf.js cannot draw (a DOCX) shows `fallback`, its type, not the preview's
 * Download note; a failed one shows "No Preview".
 */
export function ResumeThumbnail({
  source,
  version,
  fallback,
}: {
  source: TailorSource;
  version?: string;
  fallback: ReactNode;
}) {
  const [near, ref] = useNear();
  const { key, preview } = useResumePreview(source, near, version);
  return (
    <div
      ref={ref}
      aria-hidden
      className="bg-panel pointer-events-none relative w-full overflow-hidden"
      style={{ aspectRatio: THUMBNAIL_RATIO }}
    >
      {preview && !preview.pdf ? (
        <div className="flex h-full items-center justify-center">
          {preview.error ? <span className="text-note text-ink-meta">No Preview</span> : fallback}
        </div>
      ) : (
        <div className="w-full" style={{ aspectRatio: "8.5 / 11" }}>
          {preview?.pdf ? (
            <PdfPages
              key={key}
              pdf={preview.pdf}
              boxes={[]}
              selected={null}
              onSelect={() => {}}
              placeholder={<PageSkeleton />}
            />
          ) : (
            <PageSkeleton />
          )}
        </div>
      )}
    </div>
  );
}

/** Whether the element came within a screen of view, once: it stays true. */
function useNear(): [boolean, (node: HTMLDivElement | null) => void] {
  const [near, setNear] = useState(false);
  const observer = useRef<IntersectionObserver | null>(null);
  function ref(node: HTMLDivElement | null) {
    observer.current?.disconnect();
    if (!node || near) return;
    observer.current = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setNear(true);
          observer.current?.disconnect();
        }
      },
      { rootMargin: "100% 0px" },
    );
    observer.current.observe(node);
  }
  return [near, ref];
}

/** A DOCX upload: pdf.js cannot draw one, so its file downloads instead. */
function DocxNote({ id, label }: { id: string; label: string }) {
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setError(null);
    const { url, error } = await getResumeFileUrl(id, true);
    if (url) openDownload(url);
    else setError(error ?? "Could not download the resume.");
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <p className="text-body text-ink-meta">
        WorkIt shows PDF resumes here. Download {label} to open it.
      </p>
      <Button variant="secondary" size="sm" onClick={download}>
        <FileArrowDownIcon aria-hidden className="size-4" /> Download
      </Button>
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * View for one resume in a list of them: a text button with an eye that
 * opens the resume in `ResumePreviewDialog`, titled with its name. The
 * key is the resume pickers' ("built:<id>", "uploaded:<id>"). Auto Apply's
 * Up Next (Resume column) and Generate Resume's list of resumes to start
 * from (resumes/new-resume-dialog.tsx) draw it, always shown: a View that
 * waited for the row's hover was missed (2026-11-11).
 */
export function ResumeViewButton({ name, resumeKey }: { name: string; resumeKey: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <ViewButton name={name} onClick={() => setOpen(true)} />
      <ResumePreviewDialog
        open={open}
        onOpenChange={setOpen}
        label={name}
        source={sourceOfKey(resumeKey)}
      />
    </>
  );
}

/** View's look, for a list that shows the resume its own way (Generate
 *  Resume's dialog shows it in place). Text, not a bordered button: a table
 *  row holds none (frontend/docs/design.md, which button look). */
export function ViewButton({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      title={`View ${name}`}
      aria-label={`View resume ${name}`}
      className="text-ink hover:text-brand"
    >
      <EyeIcon aria-hidden />
      View
    </Button>
  );
}

/** A picker's key ("built:<id>", "uploaded:<id>") as the preview's source. */
export function sourceOfKey(resumeKey: string): TailorSource {
  const [kind, id] = resumeKey.split(":");
  return kind === "built" ? { built_resume_id: id } : { uploaded_resume_id: id };
}
