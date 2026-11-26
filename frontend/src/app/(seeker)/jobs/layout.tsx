import { JobsRailFrame } from "./jobs-rail";
import { FilterOptionsProvider } from "./list-data";
import { getJobFacets, getJobLocations, getJobsView } from "./listings";

/** /jobs and everything under it. Draws the rail of jobs beside a job
 *  posting's page (./jobs-rail.tsx, KAN-297), and in the split view the Jobs
 *  page's header over both (KAN-519); every other page passes through as it
 *  was.
 *
 *  It starts the filter row's options in either view (KAN-916): the view
 *  changes in the browser now (./view-store), so a Card View drawn by the
 *  server may become the split view with no new draw. A layout is drawn
 *  once per visit, and the API keeps both answers, so they cost a job page
 *  opened from Home two quick reads. `view` is the cookie's: the view this
 *  draw starts in. */
export default async function JobsLayout({ children }: LayoutProps<"/jobs">) {
  const view = await getJobsView();
  return (
    <FilterOptionsProvider locations={getJobLocations()} facets={getJobFacets()}>
      <JobsRailFrame view={view}>{children}</JobsRailFrame>
    </FilterOptionsProvider>
  );
}
