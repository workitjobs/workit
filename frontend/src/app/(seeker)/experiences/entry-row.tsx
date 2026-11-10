"use client";

import { FileTextIcon, WarningIcon } from "@phosphor-icons/react/ssr";
import { useState, type MouseEvent, type ReactNode } from "react";

import { ChevronDownIcon } from "@/components/icons";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/shadcn/popover";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { EntryFields } from "@/lib/bank-actions";
import { cn } from "@/lib/cn";

import { degreeLine, entryDetails, formatDates, gapLine, rowGaps } from "./sections";

/** A bullet as a row shows it: the bank's, or this resume's own wording. */
type RowBullet = { id: string; text: string };

/**
 * One entry as every bank surface draws it (KAN-440): the Experiences page
 * and its section lists, the resume editor's panel and onboarding's resume
 * preview (KAN-732), so they cannot drift apart. The preview's copy of this
 * row had drifted: it left out the location, a school's degree and GPA,
 * coursework, an issuer and a link, the facts the student was asked to
 * check. It takes an entry's fields and its bullets, saved or not: a preview
 * entry has no ids. Closed, it is two lines: the title with its badges and
 * dates, then the place or a school's degree; a press on it opens the other
 * details and the bullets. It opens closed: every entry fully open made a
 * bank of six entries a long page, and the student reads a bank by its
 * titles.
 *
 * WHAT A ROW FLAGS IS A BADGE ON ITS TITLE LINE (KAN-740), never a line of
 * its own: `warn` adds one amber badge for each fact a resume would miss
 * ("No Start Date", "No Bullets", `rowGaps`), and `badges` the surface's own
 * (onboarding's Replaces Earlier Copy). A row had grown up to three loose
 * lines of small text in three colours (a purple "3 bullets" that looked
 * like a link, a grey "Other bullets on …" with long names cut short, an
 * amber sentence repeated on nine rows in ten), each added by a different
 * ticket and none reading as a status. The bullet count is gone (the chevron
 * says the row opens; only none matters, and that is a badge); the why of
 * the badges is said once per card (`GapSummary`); other versions are one
 * control at the right (`OtherVersions`).
 *
 * An entry with nothing more to show has no chevron and no press. Bullets
 * stop at a readable measure, since a page 1440px wide ran them past 130
 * characters a line.
 *
 * The slots are the surface's own: `lead` and `actions` sit beside the
 * heading, outside the press, so a control in them never opens the row.
 * `bullets` gives the row its own words, `bulletLead` a control before each
 * bullet, `summary` a line the closed row adds (the editor's "2 of 3
 * bullets") and `muted` a quieter title, for an entry not on the resume.
 * `open` holds the row open, with no chevron: for Scout working on the
 * entry, and for every entry of onboarding's resume preview, where the
 * student checks all of a reading before saving it, so none of it waits
 * behind a press.
 */
export function EntryRow({
  entry,
  lead,
  actions,
  badges,
  warn = false,
  open = false,
  muted = false,
  summary,
  bullets = entry.bullets,
  bulletLead,
}: {
  entry: EntryFields & { bullets: RowBullet[] };
  lead?: ReactNode;
  actions?: ReactNode;
  /** The surface's own badges, after the title and any warning. */
  badges?: ReactNode;
  /** Flag what a resume would miss, as badges after the title. */
  warn?: boolean;
  open?: boolean;
  muted?: boolean;
  /** A line the closed row adds under the place: the editor's count of
   *  the bullets this resume prints. */
  summary?: string;
  bullets?: RowBullet[];
  bulletLead?: (bullet: RowBullet) => ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  const dates = formatDates(entry);
  const place = [entry.organization, entry.location].filter(Boolean).join(" · ");
  const degree = degreeLine(entry);
  const more = entryDetails(entry).filter((line) => line !== degree);
  const opens = !open && (more.length > 0 || bullets.length > 0);
  const shown = open || opened;
  const gaps = warn ? rowGaps({ ...entry, bullets }) : [];

  const heading = (
    <>
      <span className="min-w-0 flex-1">
        {/* The badges follow the title and wrap under it where it is long */}
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={cn(
              "text-body min-w-0 font-medium break-words",
              muted ? "text-ink-muted" : "text-ink",
            )}
          >
            {entry.title}
          </span>
          {gaps.map((gap) => (
            <Badge key={gap} variant="tag" tone="warning">
              <WarningIcon aria-hidden weight="bold" className="mr-1 size-3.5" />
              No {gap}
            </Badge>
          ))}
          {badges}
        </span>
        {/* A narrow column puts the dates under the title: beside it, they
            never shrink and left the title a few letters wide on a phone. */}
        {dates && <span className="text-note text-ink-meta block @xl/main:hidden">{dates}</span>}
        {place && <span className="text-note text-ink-muted block break-words">{place}</span>}
        {degree && <span className="text-note text-ink-meta block break-words">{degree}</span>}
        {!shown && summary && <span className="text-note text-ink-meta block">{summary}</span>}
      </span>
      {dates && (
        <span className="text-note text-ink-meta hidden shrink-0 @xl/main:inline">{dates}</span>
      )}
    </>
  );

  return (
    <div>
      <div className="flex items-start gap-2">
        {lead}
        {opens ? (
          <button
            type="button"
            aria-expanded={shown}
            onClick={() => setOpened((was) => !was)}
            className="focus-visible:ring-brand-ring flex min-w-0 flex-1 items-start gap-2 rounded-xs text-left outline-none focus-visible:ring-2"
          >
            <ChevronDownIcon
              className={cn(
                "text-brand mt-1 size-4 shrink-0 transition-transform",
                !shown && "-rotate-90",
              )}
            />
            {heading}
          </button>
        ) : (
          <div className="flex min-w-0 flex-1 items-start gap-2">{heading}</div>
        )}
        {actions}
      </div>

      {shown && (more.length > 0 || bullets.length > 0) && (
        <div className={cn("mt-1 max-w-[75ch]", opens && "pl-6")}>
          {more.map((line) => (
            <p key={line} className="text-note text-ink-meta break-words">
              {line}
            </p>
          ))}
          {bullets.length > 0 && (
            <ul
              className={cn(
                "text-body text-ink-muted mt-1.5 flex flex-col gap-1",
                !bulletLead && "marker:text-brand list-disc pl-5",
              )}
            >
              {bullets.map((bullet) => (
                <li key={bullet.id} className="break-words">
                  {bulletLead ? (
                    <span className="flex items-start gap-2">
                      {bulletLead(bullet)}
                      <span className="min-w-0 flex-1">{bullet.text}</span>
                    </span>
                  ) : (
                    bullet.text
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * A card's one line about its rows' badges (`gapLine`): how many entries
 * lack something a resume needs, and that it matters before Generate. Said
 * once for the card, under its heading, where every row said it (KAN-740).
 * Shared by the Experiences cards and lists and onboarding's preview.
 */
export function GapSummary({
  entries,
}: {
  entries: readonly (EntryFields & { bullets: readonly { text: string }[] })[];
}) {
  const line = gapLine(entries);
  if (!line) return null;
  return (
    <p className="text-note text-warning mt-1 flex items-start gap-1.5">
      <WarningIcon aria-hidden weight="bold" className="mt-0.5 size-3.5 shrink-0" />
      {line}
    </p>
  );
}

/**
 * The resumes whose copy of this entry has other bullets (`otherVersions`),
 * as one small control at the row's right (KAN-740): "2 Other Versions",
 * which opens their names in full. It was a line under the entry, "Other
 * bullets on [file] Resume #3, [file] Andrew Shi Rogue Fitness Product
 * Designer Inter… and 3 more", longer than the title and cut short, with
 * links that looked like plain grey text. With `onShow` each name is a link
 * that shows that resume on Experiences (`?resume=`), as Change Resume
 * would, and a Cmd or Ctrl click opens it in a new tab; without it (the
 * resume editor's panel) the names are a list to read.
 */
export function OtherVersions({
  versions,
  onShow,
}: {
  versions: { id: string; name: string }[];
  onShow?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  if (versions.length === 0) return null;
  const count = versions.length;

  function show(event: MouseEvent, id: string) {
    // A new tab is the browser's to handle
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    setOpen(false);
    onShow?.(id);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button variant="secondary" size="xs">
            {count} Other {count === 1 ? "Version" : "Versions"}
            <ChevronDownIcon className="size-3.5" />
          </Button>
        }
      />
      <PopoverContent align="end" className="w-72 gap-2">
        <p className="text-note text-ink-meta">This entry has other bullets on:</p>
        <ul role="list" className="flex flex-col gap-1.5">
          {versions.map((version) => (
            <li key={version.id} className="text-body text-ink flex items-start gap-1.5">
              <FileTextIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
              {onShow ? (
                <a
                  href={`?resume=${encodeURIComponent(version.id)}`}
                  onClick={(event) => show(event, version.id)}
                  className="hover:text-brand focus-visible:ring-brand-ring min-w-0 rounded-xs break-words underline underline-offset-2 focus-visible:ring-2 focus-visible:outline-none"
                >
                  {version.name}
                </a>
              ) : (
                <span className="min-w-0 break-words">{version.name}</span>
              )}
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
