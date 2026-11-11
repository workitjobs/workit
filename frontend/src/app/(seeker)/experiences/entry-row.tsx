"use client";

import { WarningIcon } from "@phosphor-icons/react/ssr";
import { useState, type ReactNode } from "react";

import { ChevronDownIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import type { EntryFields } from "@/lib/bank-actions";
import { cn } from "@/lib/cn";

import { degreeLine, entryDetails, formatDates, rowGaps, toolsLine } from "./sections";

/** A bullet as a row shows it: the bank's, or this resume's own wording. */
type RowBullet = { id: string; text: string };

/**
 * One entry as every bank surface draws it (KAN-440): the Experiences page
 * and its section lists, the resume editor's panel and onboarding's resume
 * preview (KAN-732), so they cannot drift apart. The preview's copy of this
 * row had drifted: it left out the location, a school's degree and GPA,
 * coursework, an issuer and a link, the facts the student was asked to
 * check. It takes an entry's fields and its bullets, saved or not: a preview
 * entry has no ids. Closed, it is the title with its badges and dates, then
 * the place or a school's degree, and a project's tools (in italic on their
 * own line, as the resume prints them, KAN-738); a press on it opens the
 * other details and the bullets. It opens closed: every entry fully open made a
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
 * says the row opens; only none matters, and that is a badge). The badges
 * say it alone: a line on each card that said why they matter ("10 entries
 * are missing details a resume needs. Add them before you Generate a
 * resume.") was taken out as one more long line, and so was a "2 Other
 * Versions" button for copies with other bullets, which looked out of place
 * (the user's calls, 2026-11-09).
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
  const tools = toolsLine(entry);
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
        {tools && <span className="text-note text-ink-meta block break-words italic">{tools}</span>}
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
          <div className="flex min-w-0 flex-1 items-start gap-2">
            {/* A closed row with nothing to open keeps the chevron's room,
                so its title lines up with the rows above and below that
                have one (2026-11-10: a school with no details sat 24px
                left of the rest of Education). */}
            {!open && <span aria-hidden="true" className="mt-1 size-4 shrink-0" />}
            {heading}
          </div>
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
