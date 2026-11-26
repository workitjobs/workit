"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { FeedHeader } from "../jobs/feed-header";
import { FeedTransition, PendingFeed } from "../jobs/feed-transition";
import type { FeedFilters } from "../jobs/filter-query";
import { JobFilters } from "../jobs/filters";
import { useFilterOptions } from "../jobs/list-data";
import type { JobsView } from "../jobs/view";
import { useJobsView } from "../jobs/view-store";
import { SearchTopRow } from "./search-top-row";

/**
 * /search's frame in the Card View: its column, with the search's row (the
 * field, the count and the view) and the filter row over the results
 * (`children`). In the split view the layout's frame draws those
 * (../jobs/jobs-rail.tsx), and this draws the results alone. The view is
 * the browser's (../jobs/view-store, KAN-916), so a switch moves between the
 * two with no request, as ../jobs/list-views.tsx's JobsListFrame does on
 * /jobs. `count` is the Card View's, streamed in its own boundary; `extras`
 * draw nothing (the feed's memory).
 */
export function SearchListFrame({
  drawnView,
  filters,
  count,
  extras,
  children,
}: {
  drawnView: JobsView;
  filters: FeedFilters;
  count: ReactNode;
  extras: ReactNode;
  children: ReactNode;
}) {
  const view = useJobsView(drawnView);
  const options = useFilterOptions();

  if (view === "split") {
    return (
      <>
        {extras}
        {children}
      </>
    );
  }

  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      {extras}
      {/* One transition for a filter change, so the results dim the moment
          the row starts it (../jobs/feed-transition). */}
      <FeedTransition>
        {/* The search and filters stay put while the results scroll, as on
            /jobs. The heading, "Results for" the query, is in the top bar
            (../bar-title.tsx). The row is the split frame's too
            (./search-top-row.tsx). No Sort: a search has one order. */}
        <FeedHeader top={<SearchTopRow view={drawnView} count={count} />}>
          <JobFilters locations={options.locations} facets={options.facets} filters={filters} />
        </FeedHeader>
        <PendingFeed>{children}</PendingFeed>
      </FeedTransition>
    </div>
  );
}
