import { Skeleton } from "@/components/shadcn/skeleton";
import { cn } from "@/lib/cn";

import { BackLink } from "../../../back-link";
import { SEEKER_GUTTER } from "../../../gutter";
import { PageSkeleton } from "../../[resumeId]/pdf-pages";
import { DESK, DESK_BAR, DESK_PAGES } from "../../[resumeId]/slim-bar";

/**
 * An uploaded resume's page while it loads (KAN-368): the page reads the
 * resume list, then the file itself from Storage (./page.tsx), before it
 * draws anything. This is its frame (./viewer.tsx): Back (live), the title
 * row (the name, its date, Download and ⋯ as bars), the bar's box with the
 * zoom as a bar, and a page's skeleton where pdf.js will draw the file.
 * ../../../home/loading.tsx says why only the slow pages have one.
 */
export default function UploadedResumeLoading() {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <BackLink parent={{ href: "/resumes", name: "Resumes" }} />
      <div role="status">
        <span className="sr-only">Loading the resume</span>
        {/* The editor's title row (KAN-825): the name, the date, Download
            and ⋯, at the title's height */}
        <div aria-hidden="true" className="mt-4 flex h-9 items-center gap-3 @3xl/main:h-10">
          <Skeleton className="h-6 w-56 max-w-full @3xl/main:h-8" />
          <Skeleton className="ml-auto h-4 w-24" />
          <Skeleton className="h-9 w-28" />
          <Skeleton className="size-8 rounded-full" />
        </div>
        <div aria-hidden="true" className="mt-3 flex flex-col gap-4">
          <div className={DESK}>
            <div className={cn(DESK_BAR, "@max-md/main:hidden")}>
              <Skeleton className="ml-auto h-7 w-28" />
            </div>
            {/* At the pages' opening zoom, Fit Width up to 150% (1224px,
                ../../[resumeId]/zoom.tsx, which a server file cannot read) */}
            <div className={DESK_PAGES}>
              <div className="mx-auto w-full max-w-[1224px]">
                <PageSkeleton />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
