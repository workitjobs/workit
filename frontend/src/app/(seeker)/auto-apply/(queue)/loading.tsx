import { Skeleton } from "@/components/shadcn/skeleton";
import { PAGE_SEARCH } from "@/components/ui/search-field";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

/**
 * Auto Apply while its four reads land (KAN-368): the queue, the saved jobs
 * with their scores, and both resume lists (./page.tsx). Two of them score,
 * so a click on the sidebar's row drew nothing new for a while; now the
 * prefetched state below is drawn in the click's next frame
 * (../../home/loading.tsx says why only the slow pages have one). It sits
 * in this route group with the page so it covers Up Next alone: beside
 * ../info and ../answers it was the first loading boundary on their way in,
 * so a click to either drew this page's skeleton first (KAN-561).
 *
 * Under the layout's frame and tabs, which stay live (../layout.tsx): Up
 * Next's two toolbar rows as bars, and the queue's card with rows in a
 * row's shape.
 */
export default function AutoApplyLoading() {
  return (
    <section aria-label="Up Next" aria-busy="true">
      {/* The toolbar (../queue-filters.tsx): the search with Add Jobs
          at its right, then Sort, Status, Company and Match with All
          Filters and Table Settings at the right. */}
      <div aria-hidden="true" className="flex flex-wrap items-center gap-3">
        <Skeleton className={cn("h-10 rounded-full", PAGE_SEARCH)} />
        <Skeleton className="ml-auto h-9 w-28" />
      </div>
      <div aria-hidden="true" className="@container mt-3 flex items-center gap-2">
        <Skeleton className="h-9 w-36 shrink-0" />
        <Skeleton className="hidden h-9 w-36 @min-[30.5rem]:block" />
        <Skeleton className="hidden h-9 w-36 @min-[40rem]:block" />
        <Skeleton className="hidden h-9 w-36 @min-[49.5rem]:block" />
        <Skeleton className="ml-auto size-9 shrink-0 rounded-full" />
        <Skeleton className="size-9 shrink-0 rounded-full" />
      </div>
      <Card padding="none" aria-hidden="true" className="mt-4 overflow-hidden">
        <div className="border-border-subtle flex h-10 items-center gap-6 border-b px-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="ml-auto h-3 w-16" />
          <Skeleton className="h-3 w-16" />
        </div>
        <ul>
          {Array.from({ length: 4 }, (_, i) => (
            <li
              key={i}
              className="border-border-subtle flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
            >
              <Skeleton className="rounded-control size-9 shrink-0" />
              <span className="flex min-w-0 flex-1 flex-col gap-1.5">
                <Skeleton className="h-3.5 w-48 max-w-full" />
                <Skeleton className="h-3 w-28 max-w-full" />
              </span>
              <Skeleton className="h-6 w-24 shrink-0 rounded-full" />
              <Skeleton className="h-3 w-20 shrink-0" />
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}
