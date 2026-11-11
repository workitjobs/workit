import { Skeleton } from "@/components/shadcn/skeleton";
import { cn } from "@/lib/cn";

import { BackLink } from "../../../back-link";
import { SEEKER_GUTTER } from "../../../gutter";
import { PageSkeleton } from "../../[resumeId]/pdf-pages";
import { SLIM_BAR } from "../../[resumeId]/slim-bar";

/**
 * An uploaded resume's page while it loads (KAN-368): the page reads the
 * resume list, then the file itself from Storage (./page.tsx), before it
 * draws anything. This is its frame (./viewer.tsx): Back (live), the title
 * row (the name, its date and its buttons as bars), the bar's box with the
 * zoom as a bar, and a page's skeleton where pdf.js will draw the file.
 * ../../../home/loading.tsx says why only the slow pages have one.
 */
export default function UploadedResumeLoading() {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <BackLink parent={{ href: "/resumes", name: "Resumes" }} />
      <div role="status">
        <span className="sr-only">Loading the resume</span>
        <div aria-hidden="true" className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <Skeleton className="h-8 w-56 max-w-full" />
            <Skeleton className="mt-1.5 h-4 w-32" />
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-28" />
          </div>
        </div>
        <div aria-hidden="true" className="mt-4 flex flex-col gap-4">
          <div className={cn(SLIM_BAR, "@max-md/main:hidden")}>
            <Skeleton className="ml-auto h-7 w-28" />
          </div>
          {/* At the viewer's opening zoom, 100% (816px, ../../[resumeId]/zoom.tsx) */}
          <div className="mx-auto w-full max-w-[816px]">
            <PageSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}
