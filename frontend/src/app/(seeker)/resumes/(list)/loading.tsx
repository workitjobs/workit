import { cookies } from "next/headers";

import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../../gutter";
import { RESUMES_SEARCH, ResumesHeader } from "../header";
import { readResumesLayout, RESUME_GRID, RESUMES_LAYOUT_COOKIE, THUMBNAIL_RATIO } from "../view";

/**
 * Resumes while both resume lists load (KAN-561): the page's frame
 * (./page.tsx), Documents' tabs live, then the search with Generate Resume
 * and the List / Grid switch at its right, the filter row and the table
 * (../resume-list.tsx) as bars: its headings and its rows, or the grid's
 * cards, as the student's kept layout says (../view.ts): drawn as the
 * table for a student on the grid, the page jumped from one to the other
 * as it loaded. In this route group so it never stands in for the editor
 * or an upload's page, which have their own.
 */
export default async function ResumesLoading() {
  const grid = readResumesLayout((await cookies()).get(RESUMES_LAYOUT_COOKIE)?.value) === "grid";
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <ResumesHeader
        view="resumes"
        search={<Skeleton aria-hidden="true" className={cn(RESUMES_SEARCH, "h-10 rounded-full")} />}
        action={
          <>
            <Skeleton aria-hidden="true" className="h-9 w-28" />
            <Skeleton aria-hidden="true" className="h-9 w-17 rounded-full" />
          </>
        }
      />
      <div role="status">
        <span className="sr-only">Loading your resumes</span>
        {/* The real filter row (../built-resumes.tsx): Type, Company and
            Sort, then All Filters and Table Settings at the right. Type
            and Company step out of a narrow row, as the real ones do. */}
        <div aria-hidden="true" className="@container mt-3 flex items-center gap-2">
          <Skeleton className="hidden h-9 w-36 rounded-full @min-[30.5rem]:block" />
          <Skeleton className="hidden h-9 w-36 rounded-full @min-[40rem]:block" />
          <Skeleton className="h-9 w-36 rounded-full" />
          <Skeleton className="ml-auto size-9 rounded-full" />
          {!grid && <Skeleton className="size-9 rounded-full" />}
        </div>
        {grid ? (
          // The grid's cards: the page's top, then the name's two lines,
          // then the badge and the date (components/resume-row.tsx).
          <div className="@container mt-4">
            <div aria-hidden="true" className={RESUME_GRID}>
              {Array.from({ length: 8 }, (_, i) => (
                <Card key={i} padding="none" className="overflow-hidden">
                  <Skeleton
                    className="border-border-subtle w-full rounded-none border-b"
                    style={{ aspectRatio: THUMBNAIL_RATIO }}
                  />
                  <div className="p-3">
                    <Skeleton className="h-3.5 w-4/5" />
                    <Skeleton className="mt-2 h-3.5 w-2/5" />
                    <div className="mt-4 flex items-center justify-between">
                      <Skeleton className="h-6 w-20 rounded-full" />
                      <Skeleton className="h-3 w-16" />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          // The table's card (../resume-list.tsx): its headings, then 56px
          // rows with rules between them, the name and its date.
          <Card padding="none" aria-hidden="true" className="mt-4 overflow-hidden">
            <div className="border-border-subtle flex h-10 items-center gap-4 border-b px-4">
              <Skeleton className="h-3 w-12" />
              <Skeleton className="ml-auto h-3 w-24" />
              <span className="w-24" />
            </div>
            {Array.from({ length: 5 }, (_, i) => (
              <div
                key={i}
                className="border-border-subtle flex h-14 items-center gap-3 border-b px-4 last:border-b-0"
              >
                <Skeleton className="h-3.5 w-56 max-w-full" />
                <Skeleton className="ml-auto h-3 w-24 shrink-0" />
                <span className="w-24 shrink-0" />
              </div>
            ))}
          </Card>
        )}
      </div>
    </div>
  );
}
