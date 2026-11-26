import { Suspense } from "react";

import { getApplicationStages } from "../../auto-apply/applications";
import { BankPrompt } from "../bank-prompt";
import { ListDataProvider } from "../list-data";
import { drawnAt, getTailoredJobIds, isApplicant } from "../listings";

/**
 * /jobs's own layout (KAN-916): the reads its list needs that no filter,
 * sort or view changes, made once per visit. Next draws a layout again only
 * on a hard load, a refresh or an arrival from another page, never when the
 * address's query changes, so a filter or sort change asks the API for its
 * list alone (../list-data.tsx says what each read is for).
 *
 * In its own route group so a job's page (../[jobId]) reads none of it: the
 * jobs layout above both stays drawn beside a job's page in the split view,
 * and these were 4 API calls a job page opened from Home would waste.
 */
export default function JobsListLayout({ children }: LayoutProps<"/jobs">) {
  // Dated before the stages are read (../listings, drawnAt).
  const at = drawnAt();
  return (
    <ListDataProvider
      stages={getApplicationStages()}
      tailored={getTailoredJobIds()}
      canMarkApplied={isApplicant()}
      drawnAt={at}
      bankPrompt={
        // Its own boundary with no fallback, so the list never waits on it.
        <Suspense fallback={null}>
          <BankPrompt />
        </Suspense>
      }
    >
      {children}
    </ListDataProvider>
  );
}
