import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { SectionHeadingSkeleton } from "@/components/ui/section-heading";

import { FIELD_GRID, SECTION_CARD } from "../../profile/field-styles";

/**
 * One part of Application Info while it reads (KAN-561): its card as
 * bars, under the page's menu, which stays live (./layout.tsx reads
 * nothing). Up Next's own skeleton sits in ../(queue), so it never stands
 * in for this page.
 */
export default function ApplicationInfoLoading() {
  return (
    <Card role="status" padding="none" className={SECTION_CARD}>
      <span className="sr-only">Loading your application info</span>
      <div aria-hidden="true">
        <SectionHeadingSkeleton />
        <Skeleton className="mt-2 h-3.5 w-80 max-w-full" />
        <div className={FIELD_GRID}>
          {Array.from({ length: 4 }, (_, j) => (
            <div key={j} className="flex flex-col gap-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
