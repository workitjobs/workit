"use client";

import { FileArrowDownIcon } from "@phosphor-icons/react/ssr";
import { useRef, useState } from "react";

import { FileIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { getResumeFileUrl, type ResumeItem } from "@/lib/resume-actions";
import { cn } from "@/lib/cn";
import { openDownload } from "@/lib/save-file";

import { LocalDate } from "../../../local-time";
import { PageSkeleton, PdfPages } from "../../[resumeId]/pdf-pages";
import { ResumeDelete, TitleRowProvider } from "../../[resumeId]/resume-menu";
import { ResumeTitle } from "../../[resumeId]/resume-title";
import { DESK, DESK_BAR, DESK_PAGES } from "../../[resumeId]/slim-bar";
import {
  FIT,
  usePageZoom,
  usePinchZoom,
  useZoom,
  useZoomTo,
  Zoom,
  zoomWidth,
} from "../../[resumeId]/zoom";

/**
 * An uploaded resume's page (KAN-366), in the editor's layout (KAN-799)
 * and with the editor's title row (KAN-825): the name (`ResumeTitle`,
 * renamed in place with the field every resume renames with) and the
 * star after it (filled on the primary, a Make Primary button on any
 * other), then at the right when it was uploaded, Download, the page's one
 * filled button, and Delete (`ResumeDelete`, the trash, which asks first;
 * a ⋯ with Rename, Make Primary and Delete until 2026-11-19); then the
 * editor's desk (`DESK`, ../../[resumeId]/slim-bar.ts), its sticky bar
 * holding the zoom over the file. Until KAN-825 its title was larger, Make Primary, Rename
 * and Delete were bordered buttons, and "★ Primary" sat under the name.
 *
 * A PDF is drawn page by page with the editor's pdf.js preview
 * (`PdfPages`), with no click targets: an upload is read, not edited, and
 * its facts are edited in Experiences (ADR 0003). The bar holds the
 * editor's zoom control and its step (`useZoom`, kept per browser), so the
 * two pages open at one zoom (KAN-825; this page opened at 100% and kept
 * nothing until then). A DOCX cannot be drawn that way, so its place
 * holds the file's name and Download.
 *
 * Delete asks first and returns to the Resumes view.
 */
export function UploadedViewer({ resume, pdf }: { resume: ResumeItem; pdf: string | null }) {
  const name = resume.original_filename ?? "Resume";
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useZoom();
  const pages = useRef<HTMLDivElement>(null);
  const shownZoom = usePageZoom(pages, zoom);
  const zoomTo = useZoomTo(pages, setZoom);
  usePinchZoom(pages, shownZoom, zoomTo);

  async function download() {
    setError(null);
    const { url, error } = await getResumeFileUrl(resume.id, true);
    if (url) openDownload(url);
    else setError(error ?? "Could not download the resume.");
  }

  return (
    <TitleRowProvider>
      {/* The title row, the editor's (KAN-825): the name and the badge at
          the left; when it was uploaded, Download and Delete at the right. One
          row that never wraps: below @md Download keeps its glyph alone */}
      <div className="mt-4 flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <ResumeTitle
            as="h1"
            kind="uploaded"
            resumeId={resume.id}
            name={name}
            primary={resume.is_default}
          />
        </div>
        {resume.created_at && (
          <span className="text-note text-ink-meta shrink-0 whitespace-nowrap">
            <span className="@max-md/main:sr-only">Uploaded </span>
            <LocalDate at={resume.created_at} />
          </span>
        )}
        <Button size="sm" onClick={download}>
          <FileArrowDownIcon aria-hidden className="size-4" />
          <span className="@max-md/main:sr-only">Download</span>
        </Button>
        <ResumeDelete resumeId={resume.id} name={name} />
      </div>

      <div className="mt-3 flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}

        {pdf ? (
          // The editor's desk (`DESK`, ../../[resumeId]/slim-bar.ts): its bar
          // holds this page's one tool, the zoom, at its end where the
          // editor's is, and the page lies on its grey. A DOCX has no page to
          // zoom, so no desk; nor a bar under @md, where even the 50% step
          // (408px) is wider than the page. The page's skeleton shows until
          // pdf.js draws, as ./loading.tsx shows it
          <div className={DESK}>
            <div className={cn(DESK_BAR, "@max-md/main:hidden")}>
              <div className="ml-auto">
                <Zoom zoom={zoom} shown={shownZoom} onZoom={(to) => zoomTo(to)} />
              </div>
            </div>
            <div className={cn(zoom !== FIT && DESK_PAGES)}>
              <div ref={pages} className="mx-auto w-full" style={{ maxWidth: zoomWidth(zoom) }}>
                <PdfPages
                  pdf={pdf}
                  boxes={[]}
                  selected={null}
                  onSelect={() => {}}
                  placeholder={<PageSkeleton />}
                />
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            Icon={FileIcon}
            title="This File Can't Be Shown Here"
            action={
              <Button variant="secondary" size="sm" onClick={download}>
                <FileArrowDownIcon aria-hidden className="size-4" /> Download
              </Button>
            }
          >
            WorkIt shows PDF resumes on this page. Download {name} to open it.
          </EmptyState>
        )}
      </div>
    </TitleRowProvider>
  );
}
