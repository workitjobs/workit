import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchIcon } from "@/components/icons";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { JobPage } from "../jobs/[jobId]/job-page";
import JobLoading from "../jobs/[jobId]/loading";
import { RememberFeed } from "../jobs/[jobId]/page-actions";
import { ListingsError, ListingsSkeleton } from "../jobs/listing-card";
import {
  feedQuery,
  filterEntries,
  isFiltered,
  readFilters,
  readQuery,
  type FeedFilters,
} from "../jobs/filter-query";
import {
  getJobCount,
  getJobListings,
  getSearchFacts,
  getJobsView,
  type FeedPage,
  type SearchFact,
} from "../jobs/listings";
import { ListFallback, ListViews } from "../jobs/list-views";
import type { JobsView } from "../jobs/view";
import { JobSearch } from "./job-search";
import { SearchFacts } from "./search-facts";
import { SearchListFrame } from "./search-list-frame";
import { ResultCount, ResultCountSkeleton } from "./search-top-row";

export const metadata: Metadata = {
  title: "Search Jobs",
  description: "Find your next job.",
};

/**
 * /search, where the Jobs page's field lands with the query as ?q. It asks the
 * same live feed as /jobs (../jobs/listings) for what the query names: the
 * API reads it with the role resolver (KAN-155), so "swe intern stripe" is
 * software engineer internships at Stripe or that mention it, a typo
 * corrected, newest first (backend/app/routers/jobs.py). It draws them with the
 * feed's own list and card (../jobs/feed-list) under the feed's own filters,
 * so a role looks and acts the same whichever way it was found. The API does
 * the matching, across every job: it used to happen here, inside the 50 the
 * feed had sent, so the 51st newest role could never be found (KAN-171). A
 * page holds the first 50 matches, and Load More adds the rest.
 *
 * It replaced KAN-43's mockup: a results column and a detail pane over two
 * fixtures. A scraped role has no description for a pane to show, and on a
 * phone the pane was hidden, which left a result nothing could open. Apply
 * Now on each card opens the employer's posting, as it does on /jobs.
 *
 * The heading and the filters paint at once; the count and the list stream in
 * behind placeholders in their own shape. The count is every match, not the
 * page shown, so it comes from GET /jobs/count beside the list's own request,
 * under the same filters and words. Each boundary is keyed by the query, so a
 * new search shows its placeholders straight away instead of holding the old
 * results on screen until the new ones arrive.
 *
 * The filters are the feed's own (../jobs/filter-query), sent with the words.
 * What no search changes (the filter row's options, the seeker's stages,
 * tailored resumes and account type) is read once per visit, in ./layout.tsx,
 * so a new search or filter asks the API for its results alone (KAN-916).
 *
 * The Jobs page's two views hold here too (KAN-519). In the split view the
 * results are the Jobs page's split frame (KAN-917): ./layout.tsx draws it
 * with this search's own header (the field, the count, the filters and the
 * fact chips) over the list, and this page draws only the first result beside
 * it, handing the list, the count and the facts to the frame, as /jobs does.
 * A click opens that job's page beside the list. Until KAN-917 the split view
 * was a list alone here ("List View", KAN-519's choice: the open job was to
 * be the job's own page), half the window stood empty, and a job opened from
 * it dropped the list. The page reads the results once and draws both views
 * from them (../jobs/list-views.tsx), so the view switch changes the view in
 * the browser with no request (../jobs/view-store, KAN-916).
 */

/** "128 Jobs" in the Cards view's row, once the count lands. */
async function CountOf({ count }: { count: Promise<number | null> }) {
  return <ResultCount count={await count} />;
}

/** The address Try Again reloads: this search under these filters. */
function retryHref(query: string, filters: FeedFilters) {
  return `/search?${new URLSearchParams([["q", query], ...filterEntries(filters)])}`;
}

/** What a search shows with no match, in either view. */
function NoResults({
  query,
  filters,
  facts,
}: {
  query: string;
  filters: FeedFilters;
  facts: SearchFact[];
}) {
  return (
    <EmptyState
      Icon={SearchIcon}
      title={`No Jobs Match “${query}”`}
      className="mt-4"
      action={
        <ButtonLink href="/jobs" variant="secondary" size="sm">
          Browse All Jobs
        </ButtonLink>
      }
    >
      {isFiltered(filters) || facts.length > 0
        ? "Try a different title or company name, loosen a filter, or browse every job in the feed."
        : "Try a different title or company name, or browse every job in the feed."}
    </EmptyState>
  );
}

/**
 * The results the page read, in the view shown (../jobs/list-views.tsx,
 * KAN-916): the large cards under the search's chips, or in the split view
 * the list, its count and its facts handed to the frame
 * (../jobs/jobs-rail.tsx) beside the first result. A switch of view draws
 * from this one read. The split view waits for the count, since it lands
 * in the frame's header with the list; the Card View streams it in its own
 * row (SearchListFrame).
 *
 * The open job is drawn with what its row holds (`fromList`,
 * ../jobs/[jobId]/job-view.tsx), as on /jobs: its row's score, so it is not
 * scored again, the same whether the server drew it here or a switch read
 * it.
 */
async function Results({
  view,
  results,
  count,
  facts: factsLoading,
  query,
  filters,
}: {
  view: JobsView;
  results: Promise<FeedPage>;
  count: Promise<number | null>;
  /** The filters the search's own words set (./search-facts). */
  facts: Promise<SearchFact[]>;
  query: string;
  filters: FeedFilters;
}) {
  const [page, facts] = await Promise.all([results, factsLoading]);
  const jobs = page.jobs ?? [];
  const first = jobs[0];
  return (
    <ListViews
      drawnView={view}
      jobs={jobs}
      more={page.more}
      query={feedQuery(filters, query)}
      source="feed"
      count={count}
      facts={facts}
      heading="Search Results"
      // Over the cards or the empty state, with the results rather than the
      // heading: they arrive together, so the chips never push a list down
      // that is already on screen.
      above={<SearchFacts facts={facts} filters={filters} />}
      failed={
        page.error != null ? (
          <ListingsError error={page.error} retryHref={retryHref(query, filters)} />
        ) : null
      }
      empty={jobs.length === 0 ? <NoResults query={query} filters={filters} facts={facts} /> : null}
      open={
        view === "split" && first ? (
          <Suspense fallback={<JobLoading />}>
            <JobPage
              jobId={first.id}
              listed
              fromList={{
                match:
                  first.match != null
                    ? { score: first.match, highlights: first.highlights ?? [] }
                    : null,
              }}
            />
          </Suspense>
        ) : null
      }
      loading={<JobLoading />}
    />
  );
}

export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const params = await searchParams;
  const query = readQuery(params);
  const filters = readFilters(params);
  const view = await getJobsView();

  /* Reached by submitting an empty field, or by the URL alone. No filters and
     no count, since nothing has been searched for them to narrow or count. */
  if (!query) {
    return (
      <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
        <JobSearch />

        <EmptyState
          Icon={SearchIcon}
          title="Search for a Job"
          className="mt-6"
          action={
            <ButtonLink href="/jobs" variant="secondary" size="sm">
              Browse All Jobs
            </ButtonLink>
          }
        >
          Search by job title or company name, or browse every job in the feed.
        </EmptyState>
      </div>
    );
  }

  const results = getJobListings(filters, query);
  const count = getJobCount(filters, query);
  const facts = getSearchFacts(query);
  // Keys the boundaries below: a new query or a new set of filters shows the
  // placeholders straight away.
  const key = feedQuery(filters, query);

  return (
    <SearchListFrame
      drawnView={view}
      filters={filters}
      count={
        <Suspense key={key} fallback={<ResultCountSkeleton />}>
          <CountOf count={count} />
        </Suspense>
      }
      // So a job's page can come back to these results.
      extras={<RememberFeed />}
    >
      <Suspense
        key={key}
        fallback={
          <ListFallback
            drawnView={view}
            query={key}
            split={<JobLoading />}
            cards={<ListingsSkeleton />}
          />
        }
      >
        <Results
          view={view}
          results={results}
          count={count}
          facts={facts}
          query={query}
          filters={filters}
        />
      </Suspense>
    </SearchListFrame>
  );
}
