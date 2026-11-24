import type { Metadata } from "next";
import { Suspense } from "react";

import { BriefcaseIcon } from "@/components/icons";
import { EmptyState } from "@/components/ui/empty-state";

import { JobPage } from "../[jobId]/job-page";
import JobLoading from "../[jobId]/loading";
import { RememberFeed } from "../[jobId]/page-actions";
import { CanonicalUrl } from "../canonical-url";
import { ClearFeedFilters } from "../filters";
import { ListingsError } from "../listing-card";
import {
  filtersQuery,
  isFiltered,
  listQuery,
  queryParams,
  readFilters,
  readSort,
  sortHref,
  type FeedFilters,
  type Sort,
} from "../filter-query";
import { getJobListings, getJobsView, getRecommendedPage, getSavedFilters } from "../listings";
import { JobsListFrame, ListFallback, ListViews } from "../list-views";
import type { JobsView } from "../view";

export const metadata: Metadata = {
  title: "Jobs",
  description: "Jobs matched to your profile.",
};

/* Built without a mockup, from the layout described in ../data. The feed is
 * live (../listings), narrowed on the server by the filter row's picks, which
 * live in the URL (../filter-query, ../filters); Save, Not Interested and Ask
 * WorkIt are still inert. The card and its loading and error states are
 * ../listing-card, which /search shares.
 *
 * ONE LIST, TWO ORDERS (KAN-288), chosen by ?sort=:
 *
 * - Best Match (?sort=match), the default: the jobs the filters keep, scored
 *   against the seeker's experience bank, best first (GET
 *   /jobs/recommended). With an empty bank it shows the newest first under
 *   the same filters, below BankPrompt, which asks the student to fill it.
 * - Newest (?sort=newest): the plain feed, newest first.
 *
 * These were two views, Recommended and All Jobs, behind a switcher
 * (KAN-231). They drew the same filter row and the same cards, so they read
 * as one page, and they were merged into one list with a sort. An old
 * ?view=all link opens Newest; ?view=recommended opens Best Match.
 *
 * SAVED PREFERENCES APPLY ON A FRESH VISIT ONLY. /jobs with no query at all
 * (the sidebar's link, onboarding's Start Matching) draws Best Match with the
 * seeker's saved preferences, where the filter row shows them checked and can
 * loosen them, and writes them into the URL in place (../canonical-url). From
 * then on the URL is the truth: Clear All leaves ?sort=, which is "no
 * filters", rather than bringing the saved ones back as it would if an empty
 * filter set meant "use the saved ones".
 *
 * IN ONE ROUND TRIP. This was a redirect() to that URL, so the sidebar's
 * most used link cost two: the first answer (after the preferences read)
 * held only the redirect, and the router then asked for the page again. Now
 * the page draws the redirect's target itself, from the address that target
 * would have (`shown` below), so every part of it (the Sort menu, the
 * filter row, the list's query and Load More's key) is exactly what that
 * address draws on a reload.
 *
 * A FILTER OR SORT CHANGE READS THE LIST ALONE (KAN-916). Everything that no
 * filter changes is read once per visit, in a layout, which Next does not
 * draw again when the address's query changes: the filter row's options
 * (../layout.tsx, kept by the API) and the seeker's stages, tailored resumes,
 * account type and bank prompt (./layout.tsx). This page read all of them on
 * every change: 8 API calls in the Card View, about 14 in the split view.
 *
 * TWO VIEWS OF THE LIST (KAN-519), chosen by the switch at the heading's end
 * and kept in a cookie (../view): the large cards, or the split view. This
 * page reads the list once and draws both from it (../list-views.tsx), so a
 * switch changes the view in the browser with no request for the list
 * (../view-store). The cookie says which view the server draws first, so a
 * hard load shows the chosen view with no flash of the other. In the split
 * view the layout's frame draws the heading, the filters and the rail
 * (../jobs-rail.tsx), which is what lets those stay mounted, and Best Match
 * unscored, as one job opens after another; this page adds the open job, the
 * list's first. */

/**
 * This order's first page. Best Match with an empty bank (the API's 404) is the
 * plain feed; BankPrompt above it already asks the student to fill the bank.
 */
async function firstPage(filters: FeedFilters, sort: Sort) {
  if (sort === "match") {
    const page = await getRecommendedPage(filtersQuery(filters), 0);
    if (page) return { page, query: listQuery("match", filters), plain: false };
  }
  return { page: await getJobListings(filters), query: filtersQuery(filters), plain: true };
}

/**
 * The live list and the states that stand in for it, in either view. Its own
 * async component so the page can stream: the heading and filter row paint at
 * once and this fills in behind the fallback (the last first page drawn, or
 * the skeleton), where awaiting the fetch in the page held the whole screen.
 * A Suspense boundary here rather than a route loading.tsx, which would also
 * cover /jobs/[jobId].
 *
 * In the split view the server also draws the list's first job, and starts
 * its reads the moment the list lands, with the list row's score
 * (../[jobId]/job-view.tsx, `fromList`), in its own boundary so the list
 * shows in the rail first.
 */
async function List({ filters, sort, view }: { filters: FeedFilters; sort: Sort; view: JobsView }) {
  const { page, query, plain } = await firstPage(filters, sort);
  const jobs = page.jobs ?? [];
  const first = jobs[0];
  return (
    <ListViews
      drawnView={view}
      jobs={jobs}
      more={page.more}
      query={query}
      source={plain ? "feed" : "recommended"}
      failed={
        page.error != null ? (
          <ListingsError error={page.error} retryHref={sortHref(sort, filters)} />
        ) : null
      }
      empty={jobs.length === 0 ? <NoJobs filters={filters} sort={sort} /> : null}
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

/** What a list shows with no jobs to show. Filtered, it offers Clear
 *  Filters, as Up Next's and Documents' do (KAN-823). */
function NoJobs({ filters, sort }: { filters: FeedFilters; sort: Sort }) {
  return isFiltered(filters) ? (
    <EmptyState
      Icon={BriefcaseIcon}
      title="No Jobs Match These Filters"
      className="mt-4"
      action={<ClearFeedFilters sort={sort} />}
    >
      Nothing in the feed fits every filter you picked. Loosen one, or clear them all.
    </EmptyState>
  ) : (
    <EmptyState Icon={BriefcaseIcon} title="No Jobs Yet" className="mt-4">
      New internship and new-grad jobs land here as companies post them. Check back tomorrow
      morning.
    </EmptyState>
  );
}

export default async function JobsPage({ searchParams }: PageProps<"/jobs">) {
  const params = await searchParams;
  // A fresh visit with saved preferences draws the address it stands for,
  // which ../canonical-url then puts in the address bar.
  let canonical: string | null = null;
  if (Object.keys(params).length === 0) {
    const saved = await getSavedFilters();
    if (saved && isFiltered(saved)) canonical = sortHref("match", saved);
  }
  const shown = canonical ? queryParams(canonical.slice("/jobs".length)) : params;
  const sort = readSort(shown);
  const filters = readFilters(shown);
  const view = await getJobsView();
  const query = listQuery(sort, filters);

  return (
    <JobsListFrame
      drawnView={view}
      filters={filters}
      sort={sort}
      extras={
        <>
          {canonical && <CanonicalUrl href={canonical} />}
          {/* So a job's page can go back to this list, filters and all. */}
          <RememberFeed />
        </>
      }
    >
      {/* Keyed by the order and filters, so a new pick shows the fallback
          straight away instead of holding the old list until the narrowed
          one arrives. In the Card View the fallback draws this query's last
          first page (../feed-fallback), or the skeleton when there is none. */}
      <Suspense
        key={query}
        fallback={
          <ListFallback
            drawnView={view}
            query={query}
            altQuery={sort === "match" ? filtersQuery(filters) : undefined}
            split={<JobLoading />}
          />
        }
      >
        <List filters={filters} sort={sort} view={view} />
      </Suspense>
    </JobsListFrame>
  );
}
