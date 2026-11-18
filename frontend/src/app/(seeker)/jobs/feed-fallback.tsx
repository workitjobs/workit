"use client";

import { useSyncExternalStore } from "react";

import { readKept, readSnapshot, subscribe, subscribeSnapshot } from "./feed-pages";
import { onFeed, stagesNow } from "./feed-stages";
import { ListingCard, ListingsSkeleton } from "./listing-card";
import { readStageChanges, subscribeStageChanges } from "./shown-list";
import { StillLoading } from "./still-loading";

/**
 * The Suspense fallback for the feed (KAN-287): the first page as last
 * drawn, from ./feed-pages' snapshot, while the server fetches the fresh
 * one, or the skeleton when there is no snapshot for this query. A return
 * adds the kept Load More pages below it, as ./feed-list will; a fresh
 * arrival has had those dropped (../scroll-memory.tsx), so it shows the
 * first page alone.
 *
 * `altQuery` is the plain feed's: Best Match with an empty bank draws that
 * instead (./(list)/page.tsx), so its snapshot answers either. A wait past
 * a few seconds adds a line saying it is still working (./still-loading).
 */
export function FeedFallback({ query, altQuery }: { query: string; altQuery?: string }) {
  const snapshot = useSyncExternalStore(subscribeSnapshot, readSnapshot, () => null);
  const kept = useSyncExternalStore(subscribe, readKept, () => null);
  const changes = useSyncExternalStore(subscribeStageChanges, readStageChanges, () => null);
  const match =
    snapshot && (snapshot.query === query || snapshot.query === altQuery) ? snapshot : null;
  const late = (
    <StillLoading match={new URLSearchParams(query).get("sort") === "match"} className="mt-4" />
  );
  if (!match) {
    return (
      <>
        {late}
        <ListingsSkeleton />
      </>
    );
  }

  const firstIds = new Set(match.jobs.map((job) => job.id));
  const loaded =
    kept?.query === match.query ? kept.jobs.filter((job) => !firstIds.has(job.id)) : [];
  const tailoredIds = new Set(match.tailored);
  // A job saved or applied to since the snapshot is gone from the list it
  // stands in for (./feed-stages).
  const stages = stagesNow(match.stages, changes, match.at);
  return (
    <>
      {late}
      <h2 className="sr-only">{match.source === "recommended" ? "Best Matches" : "Newest Jobs"}</h2>
      <ul className="mt-4 flex flex-col gap-3">
        {onFeed([...match.jobs, ...loaded], stages).map((job) => (
          <li key={job.id} data-job-id={job.id}>
            <ListingCard
              job={job}
              stage={stages[job.id] ?? null}
              tailored={tailoredIds.has(job.id)}
              canMarkApplied={match.canMarkApplied}
            />
          </li>
        ))}
      </ul>
    </>
  );
}
