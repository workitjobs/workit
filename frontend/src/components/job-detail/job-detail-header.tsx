import Link from "next/link";
import type { ReactNode } from "react";

import { formatPosted } from "@/app/(seeker)/jobs/format";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

import { ClosesOn } from "./closes-on";
import type { JobPosting } from "./data";
import { JobFacts } from "./job-facts";

/** The card drawn flat in the split view's panel: a box in a box read heavy. */
export const JOB_CARD_IN_PANEL =
  "in-data-split:@4xl/main:rounded-none in-data-split:@4xl/main:border-0 in-data-split:@4xl/main:p-0";

type JobDetailHeaderProps = {
  posting: JobPosting;
  /** The employer mark before the name, sized to sit on one line with it
   *  (40px; 32px read as an afterthought beside the title). A BuildingIcon `CompanyTile` for the company viewing its own
   *  posting; the same initials the feed card draws for a seeker viewing
   *  someone else's, since a job carries no logo of its own. */
  tile: ReactNode;
  /** Omit to render the company name as plain text — a company has nothing
   *  to link to on its own posting. */
  companyHref?: string;
  /** Print when the posting closes, rather than when it went up, whenever it
   *  has a closing date. The seeker page's: a deadline is what a seeker acts
   *  on. The company rail already prints its own dates, so the company page
   *  leaves this off and keeps "Posted …". The day is the viewer's own, set
   *  in the browser by `ClosesOn`, since `closesAt` is a full timestamp. */
  showDeadline?: boolean;
  /** The status badge and Edit on the company side, beside the title. The
   *  seeker page passes its bare glyphs (Save and the like, `JobCardActions`);
   *  its buttons sit in the bar pinned above this card
   *  (`[jobId]/action-bar.tsx`), where six controls once squeezed the title to
   *  a word a line (KAN-246). */
  actions?: ReactNode;
  /** The right rail this job's audience gets: `MatchRail` (`standalone`) for
   *  a seeker, `ApplicantOverviewPanel` for the company managing the
   *  posting, each its own rounded card, sitting beside the facts. Omit it
   *  (a job nothing has scored) and the facts take the full width. */
  rail?: ReactNode;
  /** The title's level. An h1 on the job's own page; an h2 where it is drawn
   *  beside a list whose page has the h1 (the split view on /jobs), and an h3
   *  in the design kit, under a group's h2. One h1 per view. */
  titleAs?: "h1" | "h2" | "h3";
  /** The top of a seeker's job panel (`JobPanel`, app/(seeker)/jobs/[jobId]/
   *  job-view.tsx), not a card of its own: the panel is the card, and the
   *  rail stands beside the whole header, from the company line down. */
  inPanel?: boolean;
};

/**
 * The single card atop a job's expanded view: who is hiring, for what,
 * where, how far along it is, its facts, and the score or applicant panel
 * the viewer's audience gets — one box rather than three stacked ones, so
 * the whole top-of-page picture reads at a glance instead of in pieces.
 *
 * The employer line sits small and above the title, the way a job board's
 * card names the company before it names the role — a little mark and a
 * name, not the full-size tile the rest of the app uses to anchor a company.
 * After it, as quiet text and not a pill, comes when the posting went up (or
 * when it closes, with `showDeadline`): the same line, classes and wording
 * as the feed card's `<JobPostingCard>`, since age is a fact about the
 * posting, not a state to flag. Location isn't repeated up here either:
 * `JobFacts` already carries it below, and the point of a small header is
 * not filling it with what the facts row says again.
 *
 * The rule below the title runs the card's full width, and the facts and the
 * rail sit together underneath it — the rail is the facts' neighbour, not the
 * title's, so it starts level with them rather than reaching up beside the
 * company tile. `rail` renders as its own rounded card rather than a rail
 * flush against this one's edge, so the two do not read as one ruled grid.
 *
 * The card is its own `@container` and breaks at `@xl` (576px of card), not
 * at a window breakpoint: the seeker shell's panel takes 256px of the window
 * and the company shell has no `@container/main` to measure. Narrower than
 * that, the rail stacks under the facts, so it never squeezes the facts into
 * a sliver beside it. `actions` end the company line at every width. The
 * seeker page's buttons sit in the bar pinned above the card, since beside the
 * title they took the row's whole width, the title wrapped a word a line and
 * the posted date ran under the buttons (KAN-246).
 *
 * `actions` and `rail` are the only things that differ between the company
 * and seeker pages that render this; everything else is shared.
 */
export function JobDetailHeader({
  posting,
  tile,
  companyHref,
  showDeadline = false,
  actions,
  rail,
  titleAs: Title = "h1",
  inPanel = false,
}: JobDetailHeaderProps) {
  const timing =
    showDeadline && posting.closesAt ? (
      <ClosesOn iso={posting.closesAt} />
    ) : posting.postedAt ? (
      formatPosted(posting.postedAt)
    ) : (
      // A live posting its board never dated, as its card says.
      "Post date not listed"
    );

  const top = (
    <div className="min-w-0">
      <div className="flex items-center gap-3">
        {/* Never narrower than itself: in a crowded row the mark was
            squeezed to an empty sliver. */}
        <span className="flex shrink-0">{tile}</span>

        {/* Under 448px of card the timing takes its own line with no dot,
            as on the feed card, rather than wrapping "ago" alone. The name
            is a size up from the timing (KAN-279): at the timing's 13px
            the employer read as small print under a 36px title. */}
        <p className="text-label text-ink-muted min-w-0 flex-1 font-normal">
          {companyHref ? (
            // Ink, not brand: a name that turns brand on hover/focus
            // rather than sitting violet at rest, the same call the feed
            // card's own company name makes.
            <Link
              href={companyHref}
              className="text-subtitle text-ink hover:text-brand focus-visible:ring-brand-ring rounded-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
            >
              {posting.companyName}
            </Link>
          ) : (
            <span className="text-subtitle text-ink">{posting.companyName}</span>
          )}
          <span aria-hidden="true" className="text-ink-faint mx-1.5 @max-md:hidden">
            ·
          </span>
          <span className="whitespace-nowrap @max-md:block">{timing}</span>
        </p>

        {/* At the company line's right end, at every width (2026-11-10):
            below 576px of card they took a row of their own under the
            title. Beside the title they squeezed it to a word a line, and
            a row of them ran under the company line (KAN-246). */}
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>

      {/* The page's name, so `text-heading` (26px, 700), as every sub-page's
          h1 is: `text-display` is for numbers (frontend/docs/design.md). */}
      <Title className="text-heading text-ink mt-2">{posting.title}</Title>
    </div>
  );

  const facts = (
    <div className="min-w-0 flex-1">
      <JobFacts posting={posting} />

      {/* Fills the space the facts leave under themselves when the rail
          beside them is taller — a line about who is hiring, not what
          the role does (that's "About the Role", further down). Capped
          at the same 68ch measure as About the Role, since with no rail
          (an unscored job) it would otherwise run the card's width. */}
      {/* A scraped job has no line about its employer apart from its
          description, so it has none here. */}
      {posting.companyAbout && (
        <p className="text-note text-ink-meta mt-4 max-w-[68ch] leading-5">
          {posting.companyAbout}
        </p>
      )}
    </div>
  );

  // In a seeker's job panel the rail stands beside the whole header, the
  // company line to the facts, and stretches to its height (2026-11-10):
  // beside the facts alone, a 200px rail left a 150px hole under two rows
  // of facts.
  if (inPanel) {
    return (
      <header className="@container flex flex-col gap-4 @xl:flex-row @xl:items-stretch @xl:gap-6">
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {top}
          <div className="border-border-subtle border-t pt-4">{facts}</div>
        </div>
        {rail}
      </header>
    );
  }

  return (
    <Card
      as="header"
      padding="lg"
      elevated={false}
      className={cn("@container flex flex-col gap-4", JOB_CARD_IN_PANEL)}
    >
      {top}
      <div className="border-border-subtle flex flex-col gap-4 border-t pt-4 @xl:flex-row @xl:items-start">
        {facts}
        {rail}
      </div>
    </Card>
  );
}
