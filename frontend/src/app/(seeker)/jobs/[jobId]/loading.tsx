import { Skeleton } from "@/components/shadcn/skeleton";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../../gutter";
import { JobActionBar } from "./action-bar";
import { JobTabs } from "./job-tabs";
import { JOB_COLUMN, JOB_PAGE_WIDTH, JobHeaderSkeleton, JobPanel } from "./job-view";

/**
 * A job posting's page while its reads land (KAN-368): the page waits on
 * the posting, the resumes, the sent resumes, the stage and the
 * requirements (./job-view.tsx, loadJobView). Opened from a card on the
 * Jobs page, a rail row, Top Matches or Auto Apply, it drew nothing new
 * until all of them answered; now the prefetched state below is drawn in
 * the click's next frame, beside the rail, which the jobs layout keeps
 * mounted (../jobs-rail.tsx). ../../home/loading.tsx says why only
 * the slow pages have one.
 *
 * The page's own frame, so the page replaces it in place: the job page's
 * width, its action bar (live: Back works while it waits) with the actions
 * as bars, and the job's panel (./job-view.tsx, JobPanel): the header as
 * JobDetailHeader draws it (the company line, the title, the facts under
 * their rule, the match tile beside them), then under a rule Key
 * Requirements and About the Role as its sections. Tailor, under this route, has its own (./tailor/
 * loading.tsx), or a job page's skeleton would stand in for it.
 *
 * On a hard load or for an id that is no posting, the page's notFound()
 * now lands inside a streamed response, so the 404 page shows with an HTTP
 * 200; the page still reads the same.
 */
export default function JobLoading() {
  return (
    <div className={cn(JOB_PAGE_WIDTH, SEEKER_GUTTER)}>
      <JobActionBar tabs={<JobTabs />}>
        <ActionsSkeleton />
      </JobActionBar>
      <JobPageSkeleton />
    </div>
  );
}

/** The bar's actions while they load: Tailor My Resume and Apply Now, each its
 *  sm button's 36px. */
function ActionsSkeleton() {
  return (
    <span aria-hidden="true" className="flex flex-wrap items-center justify-end gap-2">
      <Skeleton className="h-9 w-40" />
      <Skeleton className="h-9 w-28" />
    </span>
  );
}

/** Under the bar: the job's panel, its header, then Key Requirements and
 *  About the Role with a rule between them, as JobViewBody draws them. */
function JobPageSkeleton() {
  return (
    <div role="status" className={JOB_COLUMN}>
      <span className="sr-only">Loading the job posting</span>
      <JobPanel header={<JobHeaderSkeleton />}>
        <div aria-hidden="true" className="divide-border-subtle flex flex-col divide-y">
          {/* Key Requirements (./key-requirements-visibility.tsx): its 28px
              heading row, then three label-and-line groups of 24px lines. */}
          <div className="pb-6">
            <div className="flex h-7 items-center gap-2">
              <Skeleton className="size-6 rounded-full" />
              <Skeleton className="h-5 w-44" />
            </div>
            <div className="mt-4 flex flex-col gap-4">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <div className="flex h-6 items-center">
                    <Skeleton className="h-4 w-28" />
                  </div>
                  <div className="flex h-6 items-center">
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* About the Role: a section's heading, then its 16px lines. */}
          <div className="pt-6">
            <div className="flex h-7 items-center gap-2">
              <Skeleton className="size-6 rounded-full" />
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="mt-3 flex flex-col gap-2 text-base">
              {["w-full", "w-11/12", "w-full", "w-4/5", "w-full", "w-2/3"].map((width, i) => (
                <Skeleton key={i} className={cn("h-4", width)} />
              ))}
            </div>
          </div>
        </div>
      </JobPanel>
    </div>
  );
}
