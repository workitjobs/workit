"use client";

import { CopySimpleIcon, EnvelopeSimpleIcon } from "@phosphor-icons/react/ssr";
import { useState, type MouseEvent } from "react";

import { STICKY_HEAD, STICKY_TH, TABLE_FILL, useFillPage } from "@/components/fill-page";
import { SearchIcon } from "@/components/icons";
import { matches, searchWords } from "@/components/resume-list";
import {
  RESUME_ACTIONS_COL,
  RESUME_DATE_COL,
  RESUME_TD,
  RESUME_TH,
  RESUME_TYPE_COL,
  ROW_ACTION,
  TargetJob,
} from "@/components/resume-row";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/shadcn/table";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { SearchField } from "@/components/ui/search-field";
import type { ApplicationStage, CoverLetter } from "@/lib/cover-letter-actions";
import { cn } from "@/lib/cn";
import { clickIsNotRows } from "@/lib/row-click";

import { LocalDate } from "../local-time";
import { RESUMES_SEARCH, ResumesHeader } from "../resumes/header";
import { STAGE_COLOR, STAGE_LABEL, type StageKey } from "../stage-colors";

/**
 * Documents' Cover Letters tab (KAN-766, step 1 of `docs/cover_letters.md`):
 * every cover letter WorkIt wrote, as a written answer on an application
 * whose form asked for one, last saved first. Read-only.
 *
 * **It is the Resumes table** (`resumes/resume-list.tsx`), so the two tabs
 * read as one page: the search on the header's row, one white card, grey
 * headings, rules between rows, and the same column widths. A letter is
 * named by its job, so the first column is the Resumes table's Target Job
 * cell (`TargetJob`: logo, role over company), then Status (the Tracker's
 * stage badge), Date Written, and Copy. A click anywhere on a row opens
 * the letter (`LetterDialog`); the role is the row's button for the
 * keyboard. The design's cards came before the Resumes tab became a table
 * (2026-11-10), so the tab follows the table instead.
 */
export function CoverLetters({ letters }: { letters: CoverLetter[] }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<CoverLetter | null>(null);
  const fill = useFillPage(true);
  const words = searchWords(query);
  const shown = letters.filter((l) =>
    matches(`${l.title ?? ""} ${l.company ?? ""} ${l.text}`, words),
  );

  return (
    <>
      <ResumesHeader
        view="cover-letters"
        search={
          letters.length > 0 && (
            <SearchField
              id="cover-letters-search"
              label="Search cover letters"
              placeholder="Search by job or text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className={RESUMES_SEARCH}
            />
          )
        }
      />
      {letters.length === 0 ? (
        <EmptyState Icon={EnvelopeSimpleIcon} title="No Cover Letters Yet" className="mt-4">
          When a job form asks for a cover letter, WorkIt writes it with your answers, and it shows
          here with the job it went to.
        </EmptyState>
      ) : shown.length === 0 ? (
        <EmptyState
          Icon={SearchIcon}
          title="No Matching Cover Letters"
          className="mt-4"
          action={
            <Button variant="secondary" size="sm" onClick={() => setQuery("")}>
              Clear Search
            </Button>
          }
        >
          None of your cover letters match this search.
        </EmptyState>
      ) : (
        <Card padding="none" className="@container mt-4 overflow-hidden">
          <Table
            aria-label="Your Cover Letters"
            containerRef={fill}
            containerClassName={TABLE_FILL}
            className="table-fixed"
          >
            <TableHeader className={STICKY_HEAD}>
              <TableRow className="hover:bg-transparent">
                <TableHead className={cn(RESUME_TH, STICKY_TH)}>Job</TableHead>
                <TableHead className={cn(RESUME_TH, STICKY_TH, RESUME_TYPE_COL)}>
                  <span className="hidden @2xl:inline">Status</span>
                </TableHead>
                <TableHead className={cn(RESUME_TH, STICKY_TH, RESUME_DATE_COL)}>
                  <span className="@2xl:hidden">Written</span>
                  <span className="hidden @2xl:inline">Date Written</span>
                </TableHead>
                <TableHead className={cn(STICKY_TH, RESUME_ACTIONS_COL)}>
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.map((letter) => (
                <LetterRow
                  key={`${letter.job_id}/${letter.name}`}
                  letter={letter}
                  onOpen={() => setOpen(letter)}
                />
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <LetterDialog letter={open} onClose={() => setOpen(null)} />
    </>
  );
}

/** The job's role, or what the form called the question when the posting
 *  has no title. */
function roleOf(letter: CoverLetter) {
  return letter.title ?? letter.label;
}

function LetterRow({ letter, onOpen }: { letter: CoverLetter; onOpen: () => void }) {
  function open(event: MouseEvent<HTMLTableRowElement>) {
    if (clickIsNotRows(event.currentTarget, event.target as Element)) return;
    onOpen();
  }
  const role = (
    <button
      type="button"
      onClick={onOpen}
      title={roleOf(letter)}
      className="text-label text-ink hover:text-brand focus-visible:ring-brand-ring max-w-full cursor-pointer truncate rounded-xs text-left font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
    >
      {roleOf(letter)}
    </button>
  );
  return (
    <TableRow onClick={open} className="group hover:bg-hover h-14 cursor-pointer">
      <TableCell className={cn(RESUME_TD, "overflow-hidden py-2")}>
        <TargetJob
          role={role}
          company={
            letter.company
              ? { name: letter.company, logoUrl: letter.logo_url, domain: letter.company_domain }
              : null
          }
        />
      </TableCell>
      <TableCell className={cn(RESUME_TD, RESUME_TYPE_COL)}>
        <span className="hidden @2xl:inline-flex">
          <StageBadge stage={letter.stage} />
        </span>
      </TableCell>
      <TableCell className={cn(RESUME_TD, "overflow-hidden")}>
        {letter.answered_at && <LocalDate at={letter.answered_at} />}
      </TableCell>
      <TableCell className="pr-2 pl-0">
        <div className="flex justify-end">
          <CopyButton text={letter.text} name={roleOf(letter)} />
        </div>
      </TableCell>
    </TableRow>
  );
}

/** Queue stages, which the Tracker's five have no colour for (Auto Apply's
 *  names, `auto-apply/activity-list.tsx`). */
const QUEUE_LABEL: Record<Exclude<ApplicationStage, StageKey>, string> = {
  queued: "Queued",
  needs_you: "Needs You",
  skipped: "Skipped",
};

/** The application's stage, as the Tracker's badge draws it. */
function StageBadge({ stage }: { stage: ApplicationStage }) {
  if (stage in STAGE_COLOR) {
    const key = stage as StageKey;
    return <Badge tone={STAGE_COLOR[key].tone}>{STAGE_LABEL[key]}</Badge>;
  }
  return <Badge tone="inert">{QUEUE_LABEL[stage as Exclude<ApplicationStage, StageKey>]}</Badge>;
}

/** Copy the letter's text, with the outcome in the tooltip. */
function CopyButton({ text, name }: { text: string; name: string }) {
  const [said, setSaid] = useState<string | null>(null);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setSaid("Copied");
    } catch {
      setSaid("Couldn't copy");
    }
    setTimeout(() => setSaid(null), 2000);
  }
  return (
    <IconButton
      label={`Copy the cover letter for ${name}`}
      tooltip={said ?? "Copy"}
      className={ROW_ACTION}
      onClick={copy}
    >
      <CopySimpleIcon aria-hidden className="size-4" />
    </IconButton>
  );
}

/**
 * One letter, read-only, over the list: the job as its title, the stage
 * and the day it was written, the text at reading width, then Copy and
 * Open Application (the application's own page, where its written answers
 * and the resume it went with are).
 */
function LetterDialog({ letter, onClose }: { letter: CoverLetter | null; onClose: () => void }) {
  const [copied, setCopied] = useState<string | null>(null);
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied("Copied.");
    } catch {
      setCopied("Couldn't copy. Select the text instead.");
    }
  }
  return (
    <Dialog
      open={letter != null}
      onOpenChange={(open) => {
        if (open) return;
        setCopied(null);
        onClose();
      }}
    >
      <DialogContent className="flex max-h-[85vh] flex-col sm:max-w-2xl">
        {letter && (
          <>
            <DialogHeader>
              <DialogTitle className="text-subtitle pr-8 font-semibold">
                {letter.company ? `Cover Letter for ${letter.company}` : "Cover Letter"}
              </DialogTitle>
              <DialogDescription className="flex flex-wrap items-center gap-2">
                <span>{roleOf(letter)}</span>
                <StageBadge stage={letter.stage} />
                {letter.answered_at && (
                  <span>
                    Written <LocalDate at={letter.answered_at} />
                  </span>
                )}
              </DialogDescription>
            </DialogHeader>
            <div className="text-body text-ink min-h-0 max-w-(--measure-prose) flex-1 overflow-y-auto whitespace-pre-wrap">
              {letter.text}
            </div>
            <DialogFooter className="items-center">
              {copied && (
                <p role="status" className="text-note text-ink-muted sm:mr-auto">
                  {copied}
                </p>
              )}
              <Button variant="secondary" onClick={() => copy(letter.text)}>
                <CopySimpleIcon aria-hidden />
                Copy
              </Button>
              <ButtonLink href={`/applications/${encodeURIComponent(letter.job_id)}`}>
                Open Application
              </ButtonLink>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
