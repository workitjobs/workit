"use client";

import { Suspense, use, useEffect, useState, type ReactNode } from "react";

import { LoadFailed } from "@/components/ui/load-failed";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { FeedFallback } from "./feed-fallback";
import { FeedHeader } from "./feed-header";
import { FeedList } from "./feed-list";
import { FeedTransition, PendingFeed } from "./feed-transition";
import type { FeedFilters, Sort } from "./filter-query";
import { JobFilters } from "./filters";
import { JobsTopRow } from "./jobs-top-row";
import type { ListSource } from "./list-pages";
import { useFilterOptions, useListData } from "./list-data";
import type { JobListing, SearchFact } from "./listings";
import { openJob } from "./open-job";
import { RememberShownList } from "./remember-shown-list";
import type { JobsView } from "./view";
import { useJobsView } from "./view-store";

/*
 * THE JOBS PAGE DRAWS BOTH VIEWS FROM ONE LIST (KAN-916). The page reads the
 * list once ((list)/page.tsx) and hands it here with the parts only the
 * server can draw (the empty and error states, and in the split view the
 * open job); each view draws from that, so a switch is a render in the
 * browser, under 100 ms, with no request for the list. `drawnView` is the
 * view the server drew, from the cookie; the shown one is the browser's
 * (./view-store). /search draws its results the same way (KAN-917,
 * ../search/page.tsx), with its own Card View frame
 * (../search/search-list-frame.tsx) and the extras a search has: its count,
 * the filters its words set, and their chips over the cards.
 *
 * The Card View draws the page's column here: the header and filter row, the
 * empty bank's prompt and the large cards. The split view's header and rail
 * are the jobs layout's frame (./jobs-rail.tsx), which stays drawn beside a
 * job's page, so here it is only the list handed to the rail and the open
 * job beside it.
 */

/** The page's frame in the Card View: its column, header and filter row, with
 *  the list (`children`) under them. In the split view the jobs layout draws
 *  those, and this draws the list and the bank's prompt alone. `extras` draw
 *  nothing (the canonical address, the feed's memory). */
export function JobsListFrame({
  drawnView,
  filters,
  sort,
  extras,
  children,
}: {
  drawnView: JobsView;
  filters: FeedFilters;
  sort: Sort;
  extras: ReactNode;
  children: ReactNode;
}) {
  const view = useJobsView(drawnView);
  const { bankPrompt } = useListData();
  const options = useFilterOptions();

  if (view === "split") {
    return (
      <>
        {extras}
        <div className={cn("pt-4 empty:hidden", SEEKER_GUTTER)}>{bankPrompt}</div>
        {children}
      </>
    );
  }

  return (
    // The Card View stops at --container-feed (1008px with the gutters), so
    // a card is the same 944px at every width from there: its 240px match
    // rail beside a body wide enough for its actions on one row, never the
    // 1376px it reached in the 1440px dashboard column, where its facts sat
    // far apart (2026-11-09).
    <div className={cn("max-w-feed mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      {extras}
      {/* One transition for a filter change, so the feed dims the moment the
          row starts it (./feed-transition). */}
      <FeedTransition>
        {/* The search and filters stay put while the list scrolls. */}
        <FeedHeader top={<JobsTopRow view={drawnView} />}>
          <JobFilters
            locations={options.locations}
            facets={options.facets}
            filters={filters}
            sort={sort}
          />
        </FeedHeader>
        {/* An empty bank's prompt to fill or import (./bank-prompt). */}
        {bankPrompt}
        <PendingFeed>{children}</PendingFeed>
      </FeedTransition>
    </div>
  );
}

/** The list's Suspense fallback in either view: the Card View's last first
 *  page or skeleton (./feed-fallback), or the split view's job skeleton
 *  (`split`, the job page's loading.tsx, which only the server can draw).
 *  `cards` replaces the Card View's: /search's skeleton, since its chips
 *  land over the cards with them and would push a kept page down. */
export function ListFallback({
  drawnView,
  query,
  altQuery,
  split,
  cards,
}: {
  drawnView: JobsView;
  query: string;
  altQuery?: string;
  split: ReactNode;
  cards?: ReactNode;
}) {
  const view = useJobsView(drawnView);
  if (view === "split") return <div className="hidden @4xl/main:contents">{split}</div>;
  return cards ?? <FeedFallback query={query} altQuery={altQuery} />;
}

/**
 * The list the page read, in the view shown. `failed` and `empty` are the
 * server's states for an error and for no jobs; `open` the split view's open
 * job, drawn by the server when it drew the split view, else read here when
 * the student switches to it (OpenJob); `loading` its skeleton.
 *
 * /search's (KAN-917): `count` and `facts` go to the split frame's header
 * with the list; the count is a promise, which only the split view waits
 * for, as the Card View streams it in its own row. `above` draws over the
 * cards and the empty state (the search's chips), and `heading` names the
 * cards for a screen reader.
 */
export function ListViews({
  drawnView,
  jobs,
  more,
  query,
  source,
  failed,
  empty,
  open,
  loading,
  count,
  facts,
  above,
  heading,
}: {
  drawnView: JobsView;
  jobs: JobListing[];
  more: boolean;
  query: string;
  source: ListSource;
  failed: ReactNode;
  empty: ReactNode;
  open: ReactNode;
  loading: ReactNode;
  count?: Promise<number | null>;
  facts?: SearchFact[];
  above?: ReactNode;
  heading?: string;
}) {
  const view = useJobsView(drawnView);
  const data = useListData();
  const stages = use(data.stages);

  if (view === "split") {
    const first = jobs[0];
    return (
      <>
        {/* The list goes to the rail in the layout's frame (./jobs-rail.tsx). */}
        <RememberShownList
          query={query}
          source={source}
          jobs={jobs}
          more={more}
          stages={stages}
          drawnAt={data.drawnAt}
          count={count ? use(count) : undefined}
          facts={facts}
        />
        {/* The rail is the whole list below @4xl/main, so the job shows only
            from there. */}
        {first ? (
          <div className="hidden @4xl/main:contents">
            {open ?? <OpenJob job={first} loading={loading} />}
          </div>
        ) : (
          <div className={cn("w-full", SEEKER_GUTTER)}>{failed ?? empty}</div>
        )}
      </>
    );
  }

  if (failed) return failed;
  if (jobs.length === 0) {
    return (
      <>
        {above}
        {empty}
      </>
    );
  }
  return (
    <>
      {above}
      {/* The level between the page's h1 and each card's h3. The card stays
          an h3 because the company preview nests it under headings of its
          own. */}
      <h2 className="sr-only">{heading ?? (source === "feed" ? "Newest Jobs" : "Best Matches")}</h2>
      {/* The first page, and a Load More for the rest (./feed-list). */}
      <FeedList
        initial={jobs}
        more={more}
        query={query}
        stages={stages}
        tailored={use(data.tailored)}
        canMarkApplied={use(data.canMarkApplied)}
        source={source}
        drawnAt={data.drawnAt}
      />
    </>
  );
}

/** The open jobs being read, by id: one request per job however often an
 *  effect starts it (React's development mode starts each twice). */
const opening = new Map<string, Promise<ReactNode>>();

/** The open jobs read, by id, the last OPENED_KEPT: a switch back to the
 *  split view shows the job at once rather than reading it again. */
const opened = new Map<string, ReactNode>();
const OPENED_KEPT = 5;

function keepOpened(id: string, node: ReactNode) {
  opened.delete(id);
  opened.set(id, node);
  if (opened.size > OPENED_KEPT) opened.delete(opened.keys().next().value!);
}

/**
 * The list's first job, read when the student switches to the split view
 * from a Card View the server drew (./open-job.tsx): the list is already on
 * screen, so only the job is asked for, with the list's score passed along
 * rather than read again. Kept for the tab (`opened`), so a switch back and
 * forth asks once.
 */
function OpenJob({ job, loading }: { job: JobListing; loading: ReactNode }) {
  const [shown, setShown] = useState<{ id: string; node: ReactNode } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [tries, setTries] = useState(0);
  const node = shown?.id === job.id ? shown.node : opened.get(job.id);
  const ready = shown?.id === job.id || opened.has(job.id);

  useEffect(() => {
    if (ready) return;
    let live = true;
    let read = opening.get(job.id);
    if (!read) {
      const match =
        job.match != null ? { score: job.match, highlights: job.highlights ?? [] } : null;
      const id = job.id;
      read = openJob(id, match);
      opening.set(id, read);
      read.then(
        (answer) => {
          opening.delete(id);
          keepOpened(id, answer);
        },
        () => opening.delete(id),
      );
    }
    read.then(
      (answer) => {
        if (live) setShown({ id: job.id, node: answer });
      },
      () => {
        if (live) setFailed(job.id);
      },
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per job, and per Try Again
  }, [job.id, ready, tries]);

  if (failed === job.id) {
    return (
      <div className={cn("w-full py-6", SEEKER_GUTTER)}>
        <LoadFailed
          title="This Job Isn't Loading"
          onRetry={() => {
            setFailed(null);
            setTries((n) => n + 1);
          }}
        >
          The list is here, but this job could not be read. Try again in a moment.
        </LoadFailed>
      </div>
    );
  }
  return ready ? <Suspense fallback={loading}>{node}</Suspense> : loading;
}
