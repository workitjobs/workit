import { HoverPrefetchLink } from "@/components/hover-prefetch-link";

import { CompanyLogo } from "@/components/company-logo";
import { jobLogo } from "@/lib/job-logo";
import { cn } from "@/lib/cn";

import type { ApplicationStage } from "../auto-apply/actions";
import { formatPostedShort, placesOf } from "./format";
import { listingFacts } from "./listing-card";
import { MatchScoreRing, MatchScoreTile } from "./match-rail";
import type { JobListing } from "./listings";
import { NotInterestedButton } from "./not-interested-button";
import { SaveJobButton } from "./save-job-button";

/** The facts a posting states, with nothing marked for the rest. */
function stated(...facts: unknown[]): string[] {
  return facts.filter((fact): fact is string => typeof fact === "string");
}

/**
 * One role as a compact card (KAN-519, after Simplify's list), in the split
 * view's list on /jobs and /search. Laid out as a list item (2026-11-09):
 *
 *   [logo]  Title, two lines at most       [Save]  [ring ]
 *           Company                                [tier ]
 *           Place · work style · job type          [     ]
 *           pay                            posted  [     ]
 *
 * The score is a small tile down the card's right side (MatchScoreTile), the
 * large card's tile in small: the ring, the percentage and the tier, no
 * reasons (2026-11-09; a pill in the footer until then).
 *
 * BELOW 26rem OF CARD THE SCORE IS ITS RING ALONE, under Save (KAN-917), the
 * company and place stop beside it, and the title may take a third line:
 *
 *   [logo]  Title, three lines at most     [Save]
 *           Company                       [ring]
 *           Place · work style · type     [    ]
 *           pay                            posted
 *
 * The split view's list is 20rem at its narrowest (a 1180px window), and the
 * tile and Save left the title about 64px of the 296px card: "Business
 * Develop…". With the ring it has about 150px, where a title such as "2027
 * Internship - Software Engineer (AI/ML)" needs three lines. The card is its
 * own container (`@container/card`), so this follows the card's width
 * wherever it is drawn, a phone's list too.
 *
 * The logo has its column alone and every line of text starts on one edge
 * beside it. Until then the place and the type ran under the logo, a second
 * left edge; Not Interested, Save and the match stacked on the right at no
 * line's height; "Internship" took a row of its own; and the post date was a
 * green pill that outshouted the match. The date is plain grey now, the least
 * a student scans for. Ink says what a student scans for (the title, the
 * company, the pay), grey the rest. Each line is one line, cut short with its
 * whole text in a tooltip; a fact the posting does not state closes up.
 *
 * In the split view each card is edged in `border-surface`, the open one in
 * brand over its tint (jobs-rail.tsx). Tailor, Auto Apply and Apply Now sit on
 * the open job. The title is the link, and its `after` layer takes a click
 * anywhere on the card; Save sits above that layer, since a button inside a
 * link is invalid.
 */
export function CompactJobCard({
  job,
  stage,
  current = false,
}: {
  job: JobListing;
  stage: ApplicationStage | null;
  current?: boolean;
}) {
  const facts = listingFacts(job);
  // Several places read as a count ("3 locations"), the whole list in the
  // tooltip: "Novi, MI +1 more" and longer lists pushed the work style and
  // the job type off the line's end (2026-11-09).
  const places = placesOf(job.location_label ?? job.location);
  const where = places.length > 1 ? `${places.length} locations` : (places[0] ?? null);
  const place = stated(where, facts.workStyle).join(" · ");
  const [pay] = stated(facts.salary);
  const [type] = stated(facts.jobType);

  const meta = [place, type].filter(Boolean).join(" · ");
  const metaTitle = [places.join(" · "), facts.workStyle, type]
    .filter((part) => typeof part === "string" && part !== "")
    .join(" · ");

  return (
    <article
      data-current={current || undefined}
      className={cn(
        "hover:bg-hover @container/card relative transition-colors",
        current && "@4xl/main:bg-brand-tint",
      )}
    >
      {/* The grid inside the card, since a container's own classes cannot
          ask its width. */}
      <div className="grid grid-cols-[2.5rem_minmax(0,1fr)_auto_auto] gap-x-3 px-4 py-3.5 @max-[26rem]/card:grid-cols-[2.5rem_minmax(0,1fr)_auto]">
        <CompanyLogo
          name={job.company}
          src={jobLogo(job)}
          className="text-label rounded-control row-span-2 size-10 self-start"
        />
        <h3 className="text-subtitle text-ink line-clamp-2 font-medium @max-[26rem]/card:line-clamp-3">
          <HoverPrefetchLink
            href={`/jobs/${encodeURIComponent(job.id)}`}
            title={job.title}
            aria-current={current ? "page" : undefined}
            className="focus-visible:ring-brand-ring rounded-control after:absolute after:inset-0 focus-visible:ring-2 focus-visible:outline-none"
          >
            {job.title}
          </HoverPrefetchLink>
        </h3>
        <div className="relative z-2 -mt-1 -mr-1 flex gap-3 justify-self-end">
          <NotInterestedButton title={job.title} quiet />
          <SaveJobButton jobId={job.id} title={job.title} stage={stage} quiet />
        </div>
        {/* Regular (2026-11-10): at the label's medium the company read as a
          second bold line under the title. */}
        <p
          title={job.company}
          className={cn("text-label text-ink col-start-2 truncate font-normal", TEXT_END)}
        >
          {job.company}
        </p>
        {/* From here every line sits in the text column, beside the logo's
          column, never under it. */}
        {meta && (
          <p
            title={metaTitle}
            className={cn(
              "text-label text-ink-muted col-start-2 mt-1.5 truncate font-normal",
              TEXT_END,
            )}
          >
            {meta}
          </p>
        )}
        <div className="text-label col-start-2 col-end-4 mt-2.5 flex min-w-0 items-center gap-2">
          {pay && (
            <span title={pay} className="text-ink min-w-0 truncate font-medium">
              {pay}
            </span>
          )}
          {/* The age in the row's right corner, where it is easy to find; it
            never shrinks, and a long pay gives way to it instead. The clock
            moves between the server render and hydration. */}
          {job.posted_at && (
            <span suppressHydrationWarning className="text-note text-ink-meta ml-auto shrink-0">
              {formatPostedShort(job.posted_at)}
            </span>
          )}
        </div>
        {/* The score in its own column, a small tile as on the large card,
          down the card's whole height; on a narrow card its ring alone,
          under Save. */}
        {job.match != null && (
          <>
            <MatchScoreTile
              score={job.match}
              className="col-start-4 row-span-4 row-start-1 ml-1 w-[5.5rem] self-stretch @max-[26rem]/card:hidden"
            />
            <MatchScoreRing
              score={job.match}
              className="col-start-3 row-span-2 row-start-2 mt-1 hidden justify-self-end @max-[26rem]/card:block"
            />
          </>
        )}
      </div>
    </article>
  );
}

/** Where the company and place lines end: beside the score's tile, or, on a
 *  narrow card, beside its ring under Save. The pay line under them runs on
 *  under the ring. */
const TEXT_END = "col-end-4 @max-[26rem]/card:col-end-3";
