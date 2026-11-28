import { ChatTextIcon } from "@phosphor-icons/react/ssr";
import type { ReactNode } from "react";

import { FileIcon } from "@/components/icons";
import { StatTile } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";
import { Section } from "@/components/ui/section";
import { cn } from "@/lib/cn";
import type { SentResume } from "@/lib/sent-resume-actions";

import type { JobListing } from "../../jobs/listings";
import { MatchRail } from "../../jobs/match-rail";
import { LocalDate } from "../../local-time";
import { STAGE_COLOR, STAGE_LABEL, type StageKey } from "../../stage-colors";
import {
  eventsOf,
  isUpcoming,
  nextEvent,
  sortKey,
  type Application,
  type TimelineStep,
} from "../../tracker";
import { Timeline } from "../timeline";
import { SentResumeRow } from "../view-resume";
import { ApplyBy } from "./apply-by";
import { EmptySlot } from "./empty-slot";
import { StageMenu, TrackerEvents } from "./tracker-controls";

const DAY_MS = 24 * 60 * 60 * 1000;

/** One question the application asked and the answer it sent, as WorkIt
 *  Auto Apply filled it (W11, routers/sent_applications.py); `ai` on an
 *  answer AI wrote. A multi-select's answer is the options picked. */
export type SentAnswer = { question: string; answer: string | string[]; ai: boolean };
/** What the application page read: the answers, null when none was kept,
 *  "failed" when the read failed. */
export type SentAnswers = SentAnswer[] | null | "failed";

/** The card's headline: where the application stands, in a few words. */
const HEADLINE: Record<StageKey, string> = {
  saved: "Not Applied Yet",
  applied: "Waiting to Hear Back",
  interviewing: "In Interviews",
  offer: "You Have an Offer",
  rejected: "Not Moving Forward",
};

/** The strip's columns from 448px of card, by how many cards it has: a
 *  literal class each, so Tailwind sees them. */
const COLUMNS: Record<number, string> = {
  1: "@md:grid-cols-1",
  2: "@md:grid-cols-2",
  3: "@md:grid-cols-3",
};

/** Days from `from` to `to`, rounded, never below 0. Counted in elapsed
 *  time, not calendar days, so the server needs no time zone to say it.
 *  Rounded rather than cut, as the header's "Posted 8 days ago" is: cut,
 *  an application sent 47 hours ago read as waiting 1 day. */
function daysBetween(from: string, to: string | Date) {
  const end = typeof to === "string" ? sortKey(to) : to.getTime();
  return Math.max(0, Math.round((end - sortKey(from)) / DAY_MS));
}

/**
 * The Your Application tab (KAN-256): one card, built as the Jobs page card
 * is (the status, the facts and the timeline on the left, the match rail
 * flush on the right, the next-step cards along the foot), then what the
 * seeker sent, from what the API already keeps. No new table: the stage and
 * its dates are the application's row, the resumes are the sent resumes
 * linked to the job posting.
 *
 * TWO CARDS, FACTS ONLY (KAN-286), worked out on the server against the
 * request's time (`getNow`). First whether the posting is still open, then
 * how long: since the seeker applied, or, for a saved job, since the
 * posting went up (the sooner they apply, the fewer applicants are ahead).
 * Each is the app's one stat tile (components/stat-tile.tsx, KAN-828), on
 * the tinted card: its label, its figure, then a line under it.
 * They replaced counts that read 0 for every Apply ("save to apply": Apply
 * saves and applies at once) or told the student only about the past
 * ("posted before you applied"). A suggested follow-up day was tried and
 * dropped: any fixed number of days is a guess. The total applicant count
 * would fit here, but no hiring system WorkIt reads publishes it.
 */
export function YourApplication({
  app,
  job,
  sent,
  answers = null,
  now,
  matchAbove = false,
}: {
  app: Application;
  job: JobListing | null;
  /** The sent resumes linked to this job posting, newest first. */
  sent: SentResume[];
  /** What the application sent (null: none kept, as for one sent another way). */
  answers?: SentAnswers;
  now: Date;
  /** The job's panel above already shows the match (a live posting with a
   *  score), so this card leaves it out: the same ring twice on one page
   *  read as a mistake (2026-11-10). A closed posting's header has none,
   *  and the score shows here. */
  matchAbove?: boolean;
}) {
  const cards: { label: string; value: string | number; unit?: string; note?: ReactNode }[] = [];
  // Every live application has `open`; the type leaves it optional.
  if (app.open != null) {
    cards.push({
      label: "Posting",
      value: app.open ? "Open" : "Closed",
      note: app.open
        ? app.appliedOn
          ? "Still taking applications"
          : "Apply while it's open"
        : app.appliedOn
          ? "No longer taking applications"
          : "You can no longer apply",
    });
  }
  if (app.appliedOn) {
    const days = daysBetween(app.appliedOn, now);
    cards.push({
      label: "Since You Applied",
      value: days,
      unit: days === 1 ? "day" : "days",
      note: (
        <>
          Applied <LocalDate at={app.appliedOn} />
        </>
      ),
    });
  } else if (job?.posted_at) {
    const days = daysBetween(job.posted_at, now);
    cards.push({
      label: "Since It Was Posted",
      value: days,
      unit: days === 1 ? "day" : "days",
      note: (
        <>
          Posted <LocalDate at={job.posted_at} />
        </>
      ),
    });
  }
  return (
    <>
      {/* ONE TINTED CARD for the seeker's record, holding rounded white
          boxes: the status and timeline on the left with the two cards
          under them, one box each, and the match in a box of its own on the
          right (side by side from 576px of card, stacked under it). The
          boxes are the app's rounded cards on white, so the figures stand
          off the tint; ruled, square cells read as a spreadsheet. It
          replaced three loose sections that read as clutter.

          TINTED BY ITS STAGE (the board column's panel: violet for Applied,
          grey for Saved), so it reads as the seeker's record, not a second
          white card under the job's own header. */}
      <Card
        as="section"
        padding="lg"
        aria-label="Your Application"
        className={cn("@container mt-6", STAGE_COLOR[app.stage].panel)}
      >
        {/* Stretched, not top-aligned: the match box runs the full height of the
            left side, so it never stops short and leaves an empty corner. */}
        <div className="flex flex-col gap-4 @xl:flex-row">
          <div className="min-w-0 flex-1">
            {/* The stage, once, in the stage menu (KAN-413): its glyph and
                name, and the student says where it stands once the
                employer answers. A saved job's reads Saved, as the
                Tracker's rows do. A disc and the stage's name sat before
                it until KAN-824, so the card said the stage twice. */}
            <StageMenu jobId={app.id} stage={app.stage} placeholder={STAGE_LABEL.saved} />
            <h2 className="text-title text-ink mt-3">{HEADLINE[app.stage]}</h2>
            {/* No applied date here: the days-since card and the timeline
                both carry it. */}
            <p className="text-body text-ink-meta mt-1">
              {!app.appliedOn && (
                <>
                  You saved it on <LocalDate at={app.savedOn} />
                  {" · "}
                </>
              )}
              {app.resume ? <>Sent {app.resume}</> : "No resume sent through WorkIt"}
              {/* The hiring system its posting is on, which the Tracker's
                  table showed as Source until 2026-11-05. */}
              {app.source && <> · Posted on {app.source}</>}
            </p>

            {/* Before it goes in, the student's own day to apply by
                (KAN-429), which the Calendar shows. */}
            {!app.appliedOn && (
              <ApplyBy
                jobId={app.id}
                applyBy={app.applyBy ?? null}
                closesAt={app.closesAt ?? null}
              />
            )}

            <Timeline steps={timeline(app, sent, now)} horizontal className="mt-5" />

            {/* The cards: the app's one stat tile on this tinted card, a
                white box with a hairline as the match box beside it is. A
                closed posting says so here only, not in a badge too. */}
            <div className={cn("mt-5 grid gap-3", COLUMNS[cards.length])}>
              {cards.map((card) => (
                <StatTile key={card.label} on="tint" {...card} />
              ))}
            </div>
          </div>

          {app.match != null && !matchAbove && (
            <MatchRail
              score={app.match}
              highlights={app.highlights ?? []}
              standalone
              // A rounded white box on the tinted card, like the counts (the
              // rail's own fill), its ring and reasons centred in the
              // stretched height.
              className="@xl:justify-center"
            />
          )}
        </div>
      </Card>

      {/* INTERVIEWS & DATES (KAN-413): the events the student adds, and
          later the ones the email tracker proposes (docs/email_tracker.md). */}
      <TrackerEvents jobId={app.id} events={app.events} />

      {/* WHAT YOU SENT (KAN-317): the resume as the Resumes view draws its
          rows, then the answers the application asked for, in one white
          card under the heading, built as Interviews & Dates above it is
          (KAN-824: `Section`, an elevated `Card`, `EmptySlot`).
          Answers are not stored yet; the empty line holds their place so
          the section's shape does not change when they arrive. The empty
          slots were the upload dropzone's dashed outline on the grey
          ground until 2026-11-10, and read as places to drop a file.
          W11: WorkIt Auto Apply keeps each form's answers here at the
          student's Submit, so its Mac keeps none; an application sent
          another way keeps the empty line. */}
      <Section title="What You Sent">
        <Card padding="lg" className="mt-3">
          <h3 className="text-label text-ink font-semibold">Resume</h3>
          {sent.length > 0 ? (
            <ul>
              {sent.map((resume) => (
                <SentResumeRow
                  key={resume.id}
                  resume={resume}
                  appliedWith={app.sentResume?.id === resume.id}
                />
              ))}
            </ul>
          ) : (
            <EmptySlot icon={<FileIcon className="text-ink-meta size-5" />} className="mt-2">
              No resume sent yet
            </EmptySlot>
          )}

          <h3 className="text-label text-ink mt-5 font-semibold">Answers</h3>
          {answers === "failed" ? (
            <LoadFailed title="Your Answers Aren't Loading Right Now" compact className="mt-2">
              We couldn&apos;t reach what this application sent. Try again in a few minutes.
            </LoadFailed>
          ) : answers && answers.length > 0 ? (
            <dl className="divide-border-subtle mt-2 flex flex-col divide-y">
              {answers.map((a, n) => (
                <div key={n} className="py-3 first:pt-0 last:pb-0">
                  <dt className="text-body text-ink font-medium">{a.question}</dt>
                  <dd className="text-body text-ink-muted break-words whitespace-pre-line">
                    {Array.isArray(a.answer) ? a.answer.join("; ") : a.answer}
                  </dd>
                  {a.ai && (
                    <dd className="mt-1">
                      <Badge tone="neutral">Written by AI</Badge>
                    </dd>
                  )}
                </div>
              ))}
            </dl>
          ) : (
            <EmptySlot
              icon={<ChatTextIcon aria-hidden className="text-ink-meta size-5" />}
              className="mt-2"
            >
              WorkIt Auto Apply keeps the answers of each application it fills here once you submit
              it.
            </EmptySlot>
          )}
        </Card>
      </Section>
    </>
  );
}

/** A resume sent closer than this to applying went with the application:
 *  "Did You Apply?"'s Yes sends the resume and applies within a second or
 *  two. */
const ONE_ACTION_MS = 2 * 60 * 1000;

/** A save closer than this to applying came from the same click: Yes on a
 *  job never saved writes both in one statement, at one time. Two minutes
 *  here once hid a real save made a minute before applying. */
const SAME_CLICK_MS = 5 * 1000;

/** The order of steps from one action, whatever their milliseconds say. */
const RANK: Partial<Record<TimelineStep["kind"], number>> = { saved: 0, sent: 1, applied: 2 };

/**
 * Saved, each resume sent, applied, then the application's events
 * (KAN-413), oldest first. An event still ahead is an empty ring, and the
 * first of those is marked Next (`nextEvent`), as the Calendar's panel
 * marks it.
 *
 * WHAT ONE ACTION WROTE IS ONE STEP (KAN-317). Apply writes the save, the
 * sent resume and the application within a second, in no fixed order, so
 * sorting by the millisecond once drew Sent, Saved, Applied, all at 3:02
 * PM: a resume sent before the job was saved. Now a resume sent with the
 * application is the Applied step's note, and a save from the same click
 * is left out, since the student never saved the job first. The save's
 * window is seconds, the resume's minutes: a student who saves and applies
 * a minute later did two things. Steps further apart keep their own dot;
 * a tie still sorts Saved, Sent, Applied.
 */
function timeline(app: Application, sent: SentResume[], now: Date): TimelineStep[] {
  const applied = app.appliedOn ? sortKey(app.appliedOn) : null;
  const withApplying = (at: string, within = ONE_ACTION_MS) =>
    applied != null && Math.abs(sortKey(at) - applied) <= within;

  const steps: TimelineStep[] = [];
  if (!withApplying(app.savedOn, SAME_CLICK_MS)) {
    steps.push({ id: "saved", kind: "saved", title: "Saved", at: app.savedOn, state: "done" });
  }
  const alone = sent.filter((resume) => !withApplying(resume.created_at));
  for (const resume of alone) {
    steps.push({
      id: resume.id,
      kind: "sent",
      title: "Sent a Resume",
      at: resume.created_at,
      state: "done",
    });
  }
  if (app.appliedOn) {
    steps.push({
      id: "applied",
      kind: "applied",
      title: "Applied",
      at: app.appliedOn,
      // What You Sent, under this card, names the resume.
      note: alone.length < sent.length ? "Resume sent" : undefined,
      state: "done",
    });
  }
  const next = nextEvent(app, now);
  for (const event of eventsOf(app)) {
    if (event.kind === "applied") continue;
    steps.push({
      id: event.id,
      kind: event.kind,
      title: event.title,
      at: event.at,
      state: event.id === next?.id ? "next" : isUpcoming(event.at, now) ? "later" : "done",
    });
  }
  return steps.sort(
    (a, b) => sortKey(a.at) - sortKey(b.at) || (RANK[a.kind] ?? 0) - (RANK[b.kind] ?? 0),
  );
}
