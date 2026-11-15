import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { RESUMES_SEARCH, ResumesHeader } from "../resumes/header";

/**
 * Cover Letters while the letters load (KAN-819): the page's frame
 * (./page.tsx), Documents' tabs live, the search as a bar, then the table
 * (./cover-letters.tsx) as bars: its headings, and 56px rows with the job's
 * logo, its role over its company, the date and Copy's place. The Resumes tab
 * beside it had a skeleton and this one had none, so the click from one tab
 * to the other changed nothing on screen until the letters were read.
 */
export default function CoverLettersLoading() {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <ResumesHeader
        view="cover-letters"
        search={<Skeleton aria-hidden="true" className={cn(RESUMES_SEARCH, "h-10 rounded-full")} />}
      />
      <div role="status">
        <span className="sr-only">Loading your cover letters</span>
        <Card padding="none" aria-hidden="true" className="mt-4 overflow-hidden">
          <div className="border-border-subtle flex h-10 items-center gap-4 border-b px-4">
            <Skeleton className="h-3 w-10" />
            <Skeleton className="ml-auto h-3 w-24" />
            <span className="w-8" />
          </div>
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="border-border-subtle flex h-14 items-center gap-3 border-b px-4 last:border-b-0"
            >
              <Skeleton className="size-8 shrink-0 rounded" />
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <Skeleton className="h-3.5 w-56 max-w-full" />
                <Skeleton className="h-3 w-28 max-w-full" />
              </div>
              <Skeleton className="h-3 w-20 shrink-0" />
              <Skeleton className="size-8 shrink-0 rounded-full" />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
