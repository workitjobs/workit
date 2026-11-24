import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { formatCount } from "@/lib/format-count";

import type { JobsView } from "../jobs/view";
import { ViewSwitch } from "../jobs/view-switch";
import { JobSearch } from "./job-search";

/**
 * The row over /search's filters, in either view: the search field holding
 * the words, the count of every match, and the view at the right end, as the
 * Jobs page's own row (../jobs/jobs-top-row.tsx) has it. The page draws it
 * over the large cards with the count in its own Suspense boundary; the split
 * frame draws it over the list and the open job (../jobs/jobs-rail.tsx,
 * KAN-917) with the count the search's first page brought.
 *
 * The count's slot is a fixed width (88px holds "9,999 Jobs": it counts every
 * match, not the page shown), so the row does not move when the count lands.
 * It is a live region, so a screen reader hears how many jobs a search found.
 *
 * `query` is the search's words where the address has none: a job's page
 * beside the results (./query-field.tsx).
 */
export function SearchTopRow({
  view,
  count,
  query,
}: {
  view: JobsView;
  count: ReactNode;
  query?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <JobSearch query={query} />
      <span role="status" className="inline-flex w-22 shrink-0">
        {count}
      </span>
      <div className="ml-auto">
        <ViewSwitch view={view} />
      </div>
    </div>
  );
}

/** "128 Jobs", every match. Nothing when there is nothing to count (the empty
 *  state says so in words) or the API can't say. */
export function ResultCount({ count }: { count: number | null | undefined }) {
  if (!count) return null;
  return (
    <Badge variant="tag" pill>
      {formatCount(count)} {count === 1 ? "Job" : "Jobs"}
    </Badge>
  );
}

/** The count's place while the search runs: the badge's own box and type, with
 *  the text hidden, so it is the size of a two-digit count. It sits in the
 *  same fixed slot the count lands in, so swapping one for the other moves
 *  nothing. */
export function ResultCountSkeleton() {
  return (
    <span
      aria-hidden="true"
      className="bg-ink/6 text-note inline-flex animate-pulse rounded-full px-2 py-0.5 text-transparent"
    >
      00 Jobs
    </span>
  );
}
