import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";

import { BackLink } from "../../back-link";

/**
 * Written Answers while its three reads land (KAN-561), in Auto Apply's
 * frame (../layout.tsx): Back live, then one job posting's card as bars:
 * its title and company, then two questions, each a label and an answer
 * box. Up Next's own skeleton sits in ../(queue), so it never stands in
 * for this page.
 */
export default function WrittenAnswersLoading() {
  return (
    <>
      <BackLink parent={{ href: "/auto-apply", name: "Auto Apply" }} named className="group/back" />
      <div role="status" className="mt-6">
        <span className="sr-only">Loading your written questions</span>
        <Card padding="lg" aria-hidden="true">
          <div className="flex h-5.5 items-center">
            <Skeleton className="h-4 w-56 max-w-full" />
          </div>
          <div className="flex h-5 items-center">
            <Skeleton className="h-3.5 w-32" />
          </div>
          <div className="mt-4 flex flex-col gap-6">
            {Array.from({ length: 2 }, (_, i) => (
              <div key={i} className="flex flex-col gap-2">
                <Skeleton className="h-4 w-72 max-w-full" />
                <Skeleton className="rounded-control h-32 w-full" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
