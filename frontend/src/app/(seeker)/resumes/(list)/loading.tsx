import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../../gutter";
import { RESUMES_SEARCH, ResumesHeader } from "../header";

/**
 * Resumes while both resume lists load (KAN-561): the page's frame
 * (./page.tsx), Documents' tabs live, then the search with the List /
 * Grid switch at its right, the filter row and the table
 * (../resume-list.tsx) as bars: its headings and its rows. In this route
 * group so it never stands in for the editor or an upload's page, which
 * have their own.
 */
export default function ResumesLoading() {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <ResumesHeader
        view="resumes"
        search={<Skeleton aria-hidden="true" className={cn(RESUMES_SEARCH, "h-10 rounded-full")} />}
        action={<Skeleton aria-hidden="true" className="h-9 w-17 rounded-full" />}
      />
      <div role="status">
        <span className="sr-only">Loading your resumes</span>
        {/* The real row's grid (../built-resumes.tsx): the buttons take a
            second line below its @2xl. */}
        <div aria-hidden="true" className="@container mt-3">
          <div className="grid grid-cols-2 items-center gap-2 @2xl:flex">
            <Skeleton className="h-9 rounded-full @2xl:w-36" />
            <Skeleton className="h-9 rounded-full @2xl:w-28" />
            <div className="col-span-2 grid grid-cols-2 gap-2 @2xl:ml-auto @2xl:flex">
              <Skeleton className="h-9 @2xl:w-28" />
              <Skeleton className="h-9 @2xl:w-28" />
            </div>
          </div>
        </div>
        {/* The table's card (../resume-list.tsx): its headings, then rows
            with rules between them, a tile, the name and its date. */}
        <Card padding="none" aria-hidden="true" className="mt-4 overflow-hidden">
          <div className="border-border-subtle flex h-10 items-center gap-4 border-b px-4">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="ml-auto h-3 w-24" />
            <span className="w-24" />
          </div>
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="border-border-subtle flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
            >
              <Skeleton className="size-10 shrink-0" />
              <Skeleton className="h-3.5 w-56 max-w-full" />
              <Skeleton className="ml-auto h-3 w-24 shrink-0" />
              <span className="w-24 shrink-0" />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
