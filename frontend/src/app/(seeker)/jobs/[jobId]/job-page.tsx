import { notFound } from "next/navigation";

import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../../gutter";
import { ListingsError } from "../listing-card";
import { JobActionBar } from "./action-bar";
import { CompanyTab } from "./company-tab";
import { companyFromPosting } from "./description";
import { JobTabPanes, JobTabs } from "./job-tabs";
import {
  JOB_COLUMN,
  JOB_PAGE_WIDTH,
  JobViewActions,
  JobViewBody,
  JobCardActions,
  JobPanel,
  JobViewHeader,
  loadJobView,
  type FromList,
} from "./job-view";
import { BackToJobs } from "./page-actions";

/**
 * One job's page, as /jobs/[jobId] draws it (./page.tsx says what each part
 * does) and as the split view draws the list's first job on /jobs (KAN-519).
 *
 * `listed`: the job came from a list, so one that has closed since draws
 * nothing beside it, and its title is an h2 under the bar's "Jobs" h1. On its
 * own page it is not found. `fromList` is what that list's row already
 * holds, which the page then does not read again (./job-view.tsx, KAN-916).
 */
export async function JobPage({
  jobId,
  listed = false,
  fromList,
}: {
  jobId: string;
  listed?: boolean;
  fromList?: FromList;
}) {
  const view = await loadJobView(jobId, { fromList });
  const { job, error } = view;

  if (error != null) {
    return (
      <div className={cn(JOB_PAGE_WIDTH, SEEKER_GUTTER)}>
        <BackToJobs />
        <ListingsError error={error} retryHref={`/jobs/${encodeURIComponent(jobId)}`} />
      </div>
    );
  }
  if (job == null) {
    if (listed) return null;
    notFound();
  }

  // The actions, header and body are ./job-view's, which the application's
  // own page (/applications/[jobId]) draws too.
  return (
    <div className={cn(JOB_PAGE_WIDTH, SEEKER_GUTTER)}>
      {/* Back and the job's actions, held at the top while the description
          scrolls under them (./action-bar). */}
      <JobActionBar tabs={<JobTabs />}>
        <JobViewActions view={view} job={job} />
      </JobActionBar>
      {/* One white panel: the header, then the open tab's pane under a
          rule (./job-view.tsx, JobPanel). */}
      <div className={JOB_COLUMN}>
        <JobPanel
          header={
            <JobViewHeader
              job={job}
              actions={<JobCardActions view={view} job={job} notInterested />}
              titleAs={listed ? "h2" : "h1"}
              match={view.match}
            />
          }
        >
          <JobTabPanes
            overview={<JobViewBody view={view} job={job} />}
            company={
              <CompanyTab
                name={job.company}
                company={view.company}
                about={job.description ? companyFromPosting(job.description, job.company) : null}
              />
            }
          />
        </JobPanel>
      </div>
    </div>
  );
}
