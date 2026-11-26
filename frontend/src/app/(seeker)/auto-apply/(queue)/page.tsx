import type { Metadata } from "next";

import { LoadFailed } from "@/components/ui/load-failed";
import { listBuiltResumes } from "@/lib/built-resume-actions";
import { listResumes } from "@/lib/resume-actions";

import { RememberFeed } from "../../jobs/[jobId]/page-actions";
import { formatPlaces } from "../../jobs/format";
import { activityOf } from "../activity-list";
import { getApplications, getRunApplications } from "../applications";
import { getWrittenQuestions } from "../answers/questions";
import type { SavedJob } from "../add-jobs-dialog";
import { ExtensionNotice } from "../extension-notice";
import { UpNext } from "../up-next";
import { jobLogo } from "@/lib/job-logo";

export const metadata: Metadata = {
  title: "Auto Apply",
  description: "Apply to the jobs that match you, with your resume filled in for you.",
};

/**
 * /auto-apply — where the seeker sets up applying in bulk (KAN-223). The
 * pipeline it grows into is `auto-apply/architecture.md` at the repo root:
 * match, pick the resume, fill the form with the extension, record.
 *
 * It is the Queue tab, the first of Auto Apply's four (../layout.tsx,
 * which draws the frame and the tabs; this page draws neither).
 *
 * JOBS FIRST (KAN-359). Under the tabs:
 *
 *   Up Next    the queue in the order the extension takes it, each job
 *              with the resume it will go out with, which a click on it
 *              changes, and Add Jobs to queue saved ones (./up-next.tsx).
 *              Needs-you jobs stay in it, since they wait on the seeker.
 *
 * HISTORY IS ARCHIVED FOR NOW (KAN-359), its code kept: an applied job is
 * on the Applications Tracker already, so the table only repeated it, and
 * a skipped one needs nothing. A needs-you job does need the seeker and the
 * Tracker doesn't list it, so it moved to Up Next rather than going. To
 * bring History back, render <LiveActivity items={history} /> (where
 * `history` is the items that are neither queued nor needs you) in a
 * section after Up Next; ./live-activity.tsx and the table's "history"
 * variant (./activity-list.tsx) are as they were.
 *
 * NO BUTTON OVER THE QUEUE BUT ADD JOBS. Start Auto Apply sat at the
 * page's top right until 2026-10-29: it queued the seeker's 10 best
 * matches (POST .../auto-apply/batches) and opened the queue. Jobs now
 * join the queue from their own Auto Apply button or Up Next's Add Jobs,
 * and open from Up Next, where the student picks them and presses Auto
 * Apply. Manage Resumes and Add to Claude sat there too (KAN-424): each
 * queued row shows and changes its own resume.
 *
 * SETUP IS A NOTICE, ONLY WHILE IT BLOCKS (../extension-notice.tsx,
 * 2026-11-23): the Chrome extension is the one thing Auto Apply can't run
 * without, so it is asked for over the queue while it is missing and says
 * nothing once added. Application Info and Written Answers are tabs. The
 * three were a row of link cards over the queue from 2026-11-10
 * (setup-strip.tsx), which students read as three required steps. A
 * default resume and the student's Claude are optional, so the rows carry
 * them: No Resume, and a count of a row's written questions (`questions`,
 * from GET .../written-questions), whose total the notice over the queue
 * links to Written Answers (../answers/page.tsx), which offers Connect
 * Claude. A failed read of the questions leaves the counts out: Up Next
 * says when the API is down.
 *
 * UP NEXT'S TOOLBAR (../queue-filters.tsx): the search, the filters and
 * Table Settings, as every page table has; it filters and groups the rows
 * in the browser, since this page hands it the whole queue.
 *
 * It opened with a Resume List of every resume until KAN-359; the page is
 * about which jobs go out, so jobs lead it.
 *
 * WHICH RESUME A QUEUED JOB GETS: the student's pick for it (Up Next's
 * picker, kept as the sent resume the application names, `sent_resume`),
 * else the run's own rule, `pick_resume` (architecture.md, 11.3): the built
 * resume tailored to that job posting, else the default resume (built or
 * uploaded), else none (`ruleFor`). The rule is worked out here from the
 * two resume lists, for display only; the run decides when it fills the
 * form. Keep the two in step if the rule changes.
 *
 * Everything is read here, on the server, and passed through the client
 * panel; a batch or a queueing refreshes the route to redraw it. A failed
 * read says so, never a fixture (backend/CLAUDE.md).
 */
export default async function AutoApplyPage() {
  const [run, saved, built, uploaded, written] = await Promise.all([
    getRunApplications(),
    getApplications(["saved"] as const, { scored: true }),
    listBuiltResumes(),
    listResumes(),
    getWrittenQuestions(),
  ]);
  const toWriteBy = new Map(
    (written.data ?? []).map((posting) => [posting.job_id, posting.questions.length]),
  );

  const builtList = built.data ?? [];
  const uploadedList = (uploaded.resumes ?? []).filter((resume) => resume.storage_path);
  const defaultBuilt = builtList.find((resume) => resume.is_default);
  const defaultUpload = uploadedList.find((resume) => resume.is_default);
  /** The rule's pick, as a name and the picker's key. */
  const ruleFor = (jobId: string) => {
    const tailored = builtList.find((resume) => resume.job_posting_id === jobId);
    if (tailored) return { name: tailored.name, key: `built:${tailored.id}` };
    if (defaultBuilt) return { name: defaultBuilt.name, key: `built:${defaultBuilt.id}` };
    if (defaultUpload) {
      return { name: defaultUpload.original_filename, key: `uploaded:${defaultUpload.id}` };
    }
    return { name: null, key: null };
  };

  // Queue order, oldest first: the API answers newest first, but the job the
  // extension opens next belongs at the top and a newly queued one joins at
  // the bottom.
  const items = run.applications
    ? [...run.applications].reverse().map((application) => {
        const sent = application.sent_resume;
        const resume = sent
          ? {
              name: sent.name,
              key: sent.built_resume_id
                ? `built:${sent.built_resume_id}`
                : sent.uploaded_resume_id
                  ? `uploaded:${sent.uploaded_resume_id}`
                  : null,
            }
          : ruleFor(application.job.id);
        return {
          ...activityOf(application),
          resume: resume.name,
          resumeKey: resume.key,
          questions: toWriteBy.get(application.job.id) ?? 0,
        };
      })
    : [];
  // Up Next: queued jobs and needs-you ones, which wait on the seeker too.
  const queue = items.filter((item) => item.status === "queued" || item.status === "failed");

  const savedJobs: SavedJob[] = (saved.applications ?? []).map(({ job, match }) => ({
    id: job.id,
    role: job.title,
    company: job.company,
    place: formatPlaces(job.location_label ?? job.location),
    logoUrl: jobLogo(job),
    match: match ?? null,
    autoApply: job.auto_apply,
  }));

  return (
    <>
      {/* So a queued job's page goes back here, not to the feed. */}
      <RememberFeed />
      {run.error != null ? (
        <LoadFailed
          title="Your Applications Aren't Loading Right Now"
          detail={process.env.NODE_ENV === "development" ? run.error : undefined}
        >
          We couldn&apos;t reach your applications. Try again in a few minutes.
        </LoadFailed>
      ) : (
        <>
          <ExtensionNotice className="mb-4" />
          <UpNext items={queue} saved={savedJobs} />
        </>
      )}
    </>
  );
}
