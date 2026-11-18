import { getApplicationStages } from "../auto-apply/applications";
import { JobsRailFrame } from "../jobs/jobs-rail";
import { FilterOptionsProvider, ListDataProvider } from "../jobs/list-data";
import {
  drawnAt,
  getJobFacets,
  getJobLocations,
  getJobsView,
  getTailoredJobIds,
  isApplicant,
} from "../jobs/listings";

/** /search. Draws the Jobs page's split frame (../jobs/jobs-rail.tsx,
 *  KAN-917) with the search's own header, so a search from the split view
 *  keeps the frame it was typed in; in the Card View the page passes
 *  through as it was.
 *
 *  KEPT THE SAME AS ../jobs/layout.tsx (KAN-916): it starts the filter row's
 *  options in either view and passes the cookie's view, since the view
 *  changes in the browser (../jobs/view-store). A job opened from the
 *  results mounts that layout's frame in this one's place.
 *
 *  It also makes /jobs's per-visit reads (../jobs/(list)/layout.tsx): the
 *  stages, tailored resumes and account type the results need in either
 *  view, read once, so a new search or filter asks the API for its results
 *  alone, and a switch of view draws from what is on screen
 *  (../jobs/list-views.tsx). No bank prompt: a search lists jobs by its
 *  words, not by the bank. */
export default async function SearchLayout({ children }: LayoutProps<"/search">) {
  const view = await getJobsView();
  // Dated before the stages are read (../jobs/listings, drawnAt).
  const at = drawnAt();
  return (
    <FilterOptionsProvider locations={getJobLocations()} facets={getJobFacets()}>
      <ListDataProvider
        stages={getApplicationStages()}
        tailored={getTailoredJobIds()}
        canMarkApplied={isApplicant()}
        drawnAt={at}
        bankPrompt={null}
      >
        <JobsRailFrame view={view}>{children}</JobsRailFrame>
      </ListDataProvider>
    </FilterOptionsProvider>
  );
}
