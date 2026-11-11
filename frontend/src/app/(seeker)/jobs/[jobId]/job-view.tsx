import type { ReactNode } from "react";

import { CompanyLogo } from "@/components/company-logo";
import { TailorIcon } from "@/components/icons";
import { JOB_CARD_IN_PANEL, JobDetailHeader } from "@/components/job-detail/job-detail-header";
import { AskScoutButton } from "@/components/scout/scout-buttons";
import { Skeleton } from "@/components/shadcn/skeleton";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { listBuiltResumes } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { listSentResumes } from "@/lib/sent-resume-actions";

import type { ApplicationStage } from "../../auto-apply/actions";
import { getApplicationStage } from "../../auto-apply/applications";
import { placesOf } from "../format";
import { listingFacts } from "../listing-card";
import type { Highlight } from "../data";
import { getApplied, getJobListing, getJobMatch, type JobListing } from "../listings";
import { MatchRail } from "../match-rail";
import { NotInterestedButton } from "../not-interested-button";
import { SaveJobButton } from "../save-job-button";
import { factText, toPosting } from "../to-posting";
import { ApplySplitButton } from "../apply-split-button";
import { JobMoreMenu } from "../job-more-menu";
import { ApplyButton } from "../apply-button";
import { JobDescription } from "./description";
import { getCompany, type JobCompany } from "./company-tab";
import { getRequirements, KeyRequirementsCard, type Requirement } from "./key-requirements";
import { AppliedNote } from "./page-actions";
import { SentNote } from "./sent-note";
import { jobLogo } from "@/lib/job-logo";

/**
 * One live role as its job page draws it: the actions, the header and the
 * body (the sent and applied notes, the Key Requirements card, About the
 * Role). /jobs/[jobId] and the application's own page (/applications/[jobId],
 * its Job Description tab, KAN-256) both draw the role from here, so the two
 * look the same and cannot drift apart. ./page.tsx says what each part does.
 */
export type JobView = Awaited<ReturnType<typeof loadJobView>>;

/** A job's page width (2026-11-10): the Jobs page Cards view's column,
 *  `max-w-feed` (1008px with the gutters, 944px inside them), so the page
 *  reads as the card it was opened from, with the same edges: the action bar
 *  and the job's panel (`JobPanel`) take the whole 944px, the header beside
 *  its 240px match tile as the card's body beside its rail. It was `max-w-job` (800px) from
 *  2026-11-09 to keep the description's lines short, which left the page
 *  208px narrower than the cards (the user's call to match them), and the
 *  1440px dashboard column before that. In the split view's pane the page
 *  takes the pane, so the bar's rule meets the list's edge, and JOB_COLUMN
 *  holds the content under the bar to 736px. The job page and the
 *  application's own page share it, so the two stay identical. */
export const JOB_PAGE_WIDTH =
  "max-w-feed mx-auto w-full flex-1 py-6 in-data-split:@4xl/main:max-w-none in-data-split:@4xl/main:px-4!";

/** The job's content under its action bar: 736px in the split view's pane
 *  (see JOB_PAGE_WIDTH); on its own page the page is already that wide. */
export const JOB_COLUMN = "in-data-split:@4xl/main:max-w-[46rem]";

/** What the application page already knows about its job from the
 *  tracker's row: its stage and when it was applied. Null when the row is
 *  missing (the page is then not found). */
export type KnownApplication = { stage: ApplicationStage | null; appliedAt: string | null } | null;

/** No requirements to read: About the Role alone draws no card. */
const NO_REQUIREMENTS: Promise<Requirement[]> = Promise.resolve([]);

/** No Company tab: the application's page draws none. */
const NO_COMPANY: Promise<JobCompany | null> = Promise.resolve(null);

/**
 * Everything the job page reads, in parallel. `job` is null for one that has
 * closed (or never existed); `error` when the API can't be read.
 *
 * EVERY READ STARTS HERE, AT ONCE, the Key Requirements card's included
 * (getRequirements, which never rejects). A read a component makes for
 * itself begins only once the page has rendered it, after all of these.
 *
 * The application's own page (/applications/[jobId]) passes two options.
 * `descriptionOnly`: it draws About the Role alone, so the requirements are
 * not read. `application`: its tracker row, read beside this one, already
 * says the stage and when it was applied, so those two reads are skipped
 * and the row's answers taken instead. It is a promise, not the row, so the
 * tracker read and these run together rather than one after the other.
 */
export async function loadJobView(
  jobId: string,
  {
    descriptionOnly = false,
    application,
  }: { descriptionOnly?: boolean; application?: Promise<KnownApplication> } = {},
) {
  const [{ job, error }, resumes, sent, applied, stage, requirements, company, match] =
    await Promise.all([
      getJobListing(jobId),
      listBuiltResumes(),
      listSentResumes(),
      application
        ? application.then((known) => known && { appliedAt: known.appliedAt })
        : getApplied(jobId),
      application ? application.then((known) => known?.stage ?? null) : getApplicationStage(jobId),
      descriptionOnly ? NO_REQUIREMENTS : getRequirements(jobId),
      descriptionOnly ? NO_COMPANY : getCompany(jobId),
      getJobMatch(jobId),
    ]);
  // The sent resumes linked to this posting, newest first, so the first is
  // the last one sent.
  const sentHere = (sent.data ?? []).filter((s) => s.job_posting_id === job?.id);
  return {
    job,
    error,
    stage,
    applied,
    sent: sentHere,
    tailored: resumes.data?.some((r) => r.job_posting_id === job?.id) ?? false,
    requirements,
    company,
    match,
  };
}

/** The job's actions, for JobActionBar: Auto Apply where it
 *  can fill the form, Tailor My Resume and Apply Now. What only keeps or sets
 *  the job aside sits on its card (JobCardActions), after Simplify, so the bar
 *  holds one row beside the tabs.
 *
 *  BELOW md APPLY NOW COMES FIRST, ACROSS THE PAGE (KAN-569), with Auto Apply
 *  and Tailor filling the row under it (each on its own row where the two do
 *  not fit): wrapped in this order, the bar took three rows and the one
 *  primary action was the last thing found.
 *  `data-phone-first` tells the bar to give the actions a row of their own. */
export function JobViewActions({ view, job }: { view: JobView; job: JobListing }) {
  const { stage, applied, tailored } = view;
  return (
    <>
      <div
        data-phone-first
        className="contents max-md:flex max-md:basis-full max-md:flex-wrap max-md:gap-2 max-md:*:grow"
      >
        <ButtonLink
          href={`/jobs/${encodeURIComponent(job.id)}/tailor`}
          variant="secondary"
          size="sm"
          className="shrink-0"
        >
          <TailorIcon className="size-4" />
          {tailored ? "Tailored Resume" : "Tailor My Resume"}
        </ButtonLink>
      </div>
      {/* One Apply where auto apply can fill the form (Greenhouse for now):
          Auto Apply, with Apply Manually under its arrow
          (../apply-split-button.tsx); Apply Now everywhere else. */}
      {job.auto_apply ? (
        <ApplySplitButton
          jobId={job.id}
          title={job.title}
          company={job.company}
          applyUrl={job.apply_url}
          stage={stage}
          canMarkApplied={applied != null}
          applied={applied?.appliedAt != null}
          className="max-md:order-first max-md:basis-full max-md:*:first:grow"
        />
      ) : (
        <ApplyButton
          jobId={job.id}
          title={job.title}
          applyUrl={job.apply_url}
          canMarkApplied={applied != null}
          applied={applied?.appliedAt != null}
          showsSent
          className="shrink-0 max-md:order-first max-md:basis-full"
        />
      )}
    </>
  );
}

/** The job card's bare glyphs, at its top right, in the compact card's order:
 *  Ask Scout, then Not Interested on the job's own page (inert, as on the compact
 *  card) and Save. gap-4 clears each glyph's tap area. */
export function JobCardActions({
  view,
  job,
  notInterested = false,
}: {
  view: JobView;
  job: JobListing;
  notInterested?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <AskScoutButton id={job.id} title={job.title} company={job.company} quiet />
      {notInterested && <NotInterestedButton title={job.title} quiet />}
      <SaveJobButton jobId={job.id} title={job.title} stage={view.stage} quiet />
      <JobMoreMenu
        jobId={job.id}
        title={job.title}
        company={job.company}
        canMarkApplied={view.applied != null}
        applied={view.applied?.appliedAt != null}
      />
    </div>
  );
}

/** Who is hiring, the title and the facts, the top of the job's panel
 *  (`JobPanel`), and beside them the match tile its card in the feed shows
 *  (`match`, 2026-11-10), at the card's 240px and in the card's own style
 *  (a grey tile, the ring over its tier and reasons), stretched to the
 *  header's height: the page reads as the card it was opened from. It was
 *  a bordered white box beside the facts alone, which left a hole under
 *  them and drew the rail a second way. No tile without a score (signed
 *  out, an empty bank), as the card then draws none either, and none in
 *  the split view's pane (hidden by `in-data-split`, as the page renders
 *  the same there), whose list card beside it shows it.
 *  `titleAs` is h2 beside the list on /jobs, where the bar's "Jobs" is the h1. */
export function JobViewHeader({
  job,
  actions,
  titleAs,
  match = null,
}: {
  job: JobListing;
  actions?: ReactNode;
  titleAs?: "h1" | "h2";
  match?: { score: number; highlights: Highlight[] } | null;
}) {
  return (
    <JobDetailHeader
      posting={toPosting(job)}
      titleAs={titleAs}
      inPanel
      rail={
        match && (
          <MatchRail
            score={match.score}
            highlights={match.highlights}
            // The panel's padding is the tile's margin. Not in the split
            // view's pane: the list card beside it shows it.
            className="p-0 in-data-split:@4xl/main:hidden"
          />
        )
      }
      // The employer's own logo, as on the card, at the header's 40px; its
      // initials when it has none.
      tile={
        <CompanyLogo
          name={job.company}
          src={jobLogo(job)}
          className="text-label rounded-control size-10"
        />
      }
      actions={actions}
    />
  );
}

/** JobViewHeader while the posting loads (./loading.tsx, and the
 *  application's page's): the company line, the title and the facts under
 *  their rule, as JobDetailHeader draws them in the panel, each a bar of
 *  its line's height, and the match tile beside them, so the panel is its
 *  own size and the page under it holds still. */
export function JobHeaderSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="@container flex flex-col gap-4 @xl:flex-row @xl:items-stretch @xl:gap-6"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Skeleton className="rounded-control size-10 shrink-0" />
            <Skeleton className="h-4 w-48" />
          </div>
          {/* The title's 32px lines: two below 448px of card, where nearly
              every title wraps, one above. */}
          <div className="mt-2 flex h-8 items-center">
            <Skeleton className="h-6 w-3/4" />
          </div>
          <div className="flex h-8 items-center @md:hidden">
            <Skeleton className="h-6 w-1/2" />
          </div>
        </div>
        <div className="border-border-subtle grid grid-cols-2 gap-x-4 gap-y-2.5 border-t pt-4 @md:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-5 w-4/5" />
          ))}
        </div>
      </div>
      {/* The match tile, at its 240px, as MatchRail draws it in the panel. */}
      <Skeleton className="rounded-card hidden w-60 shrink-0 @xl:block in-data-split:@4xl/main:hidden" />
    </div>
  );
}

/** The job's panel with its header alone, while the posting loads (the
 *  application's page's loading frame, whose body is its own). */
export function JobViewHeaderSkeleton() {
  return <JobPanel header={<JobHeaderSkeleton />} />;
}

/** Between the panel's parts: a rule across the panel. */
const PANEL_RULE = "border-border-subtle mt-6 border-t pt-6";

/**
 * The whole posting in one white panel (2026-11-10), as Jobright's job page
 * is: the header (JobViewHeader) and, under a rule across the panel, the
 * open tab's pane (the Overview's sections, JobViewBody, or the Company
 * tab). It was three cards, a header with its rail and two narrower cards
 * under it (Key Requirements, About the Role) that stopped where the rail
 * started, so an empty column ran down the page's right side, and the page
 * read as parts placed one after another. Flat in the split view's pane
 * (`JOB_CARD_IN_PANEL`), where the pane is the panel.
 */
export function JobPanel({
  header,
  children,
  className,
}: {
  /** None on the application page's Job Description tab, whose header is
   *  its own panel above the tabs. */
  header?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <Card as="article" padding="lg" elevated={false} className={cn(JOB_CARD_IN_PANEL, className)}>
      {header}
      {/* A pane that opens on a titled section (the Company tab's) starts
          at the rule's padding, its own top margin dropped. */}
      {children && (
        <div className={cn(header && PANEL_RULE, "[&>section:first-child]:mt-0")}>{children}</div>
      )}
    </Card>
  );
}

/** Under the header, in the job's panel: what was sent and when it was
 *  applied to, the Key Requirements section, and About the Role, each a
 *  section of the panel with a rule between them, across its whole width.
 *  `descriptionOnly` keeps About the Role alone: the application page's Job
 *  Description tab (KAN-256), where the notes and the checklist are the
 *  application's business, not the posting's, and pushed the description
 *  down. */
export function JobViewBody({
  view,
  job,
  descriptionOnly = false,
}: {
  view: JobView;
  job: JobListing;
  descriptionOnly?: boolean;
}) {
  const { sent, applied, requirements } = view;
  const lastSent = sent[0];
  const places = placesOf(job.location_label ?? job.location);
  const notes = !descriptionOnly && (lastSent || applied?.appliedAt);

  return (
    <div className="divide-border-subtle flex flex-col divide-y [&>*]:py-6 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0">
      {notes && (
        <div className="[&>p:first-child]:mt-0">
          {lastSent && <SentNote name={lastSent.name} at={lastSent.created_at} />}
          {applied?.appliedAt && <AppliedNote at={applied.appliedAt} />}
        </div>
      )}
      {!descriptionOnly && (
        <KeyRequirementsCard
          requirements={requirements}
          minYearsExperience={job.min_years_experience}
        />
      )}

      {/* Its title is for screen readers: the Overview tab names it, and
          the description's own 20px section headings (description.tsx)
          carry it on screen, as Jobright's do. The block under the title
          starts at the section's top, its margins dropped. */}
      <section
        aria-label="About the Role"
        className="[&>.sr-only+*]:mt-0 [&>.sr-only+*>:first-child]:mt-0"
      >
        <SectionHeading className={job.description ? "sr-only" : undefined}>
          About the Role
        </SectionHeading>
        {/* The card names one place and how many more; here, all of them. */}
        {places.length > 1 && (
          <p className="text-ink mt-3 text-base">Open in {places.join(" · ")}.</p>
        )}
        {job.description ? (
          <JobDescription
            text={job.description}
            company={job.company}
            applyUrl={job.apply_url}
            pay={factText(listingFacts(job).salary) || null}
            // The job's own page has a Company tab; the application's
            // Job Description tab has none, so it keeps the section.
            companyElsewhere={!descriptionOnly}
          />
        ) : (
          <p className="text-body text-ink-meta mt-3">
            This posting has no description here. Apply Now opens it on {job.company}&apos;s site.
          </p>
        )}
      </section>
    </div>
  );
}
