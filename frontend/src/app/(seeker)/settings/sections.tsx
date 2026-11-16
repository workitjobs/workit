import { Suspense } from "react";

import { Skeleton } from "@/components/shadcn/skeleton";
import { Card } from "@/components/ui/card";
import { SectionHeadingSkeleton } from "@/components/ui/section-heading";

import { IntegrationsSection } from "./integrations/section";
import { NotificationsSection } from "./notifications/section";
import { PersonalSection } from "./personal/section";
import { PreferencesSection } from "./preferences/section";
import { SecuritySection } from "./security/section";

/**
 * Every Settings section, drawn on the server and handed to the modal
 * (./settings-modal.tsx), which shows one and keeps the rest mounted
 * (KAN-364). Both ways into Settings call this: ./layout.tsx on a hard load
 * and ../@modal/(.)settings/layout.tsx on a soft navigation.
 *
 * EACH SECTION THAT READS STREAMS IN ITS OWN <Suspense> (KAN-368). Personal
 * Details reads the profile and the photo, Job Preferences the saved
 * filters and the role options (the facets and the locations),
 * Integrations whether the student's Claude is connected, and with no
 * boundary the modal opened only once the slowest of those had answered.
 * Now the route's layout awaits nothing, so the modal opens as soon as the
 * route's first bytes arrive, over each section's skeleton: its own card
 * and heading with bars where the fields go. A section's form mounts once,
 * when its data arrives, so its unsaved-changes guard (./unsaved-changes)
 * only ever starts clean; a refresh after a save keeps the drawn form, since
 * React never falls back a boundary that is already showing.
 *
 * NO loading.tsx FOR THE MODAL. A loading.tsx in ../@modal/(.)settings sits
 * inside that folder's layout, which is what draws the modal, so it wraps
 * only the section's empty page: one drawing the modal as its fallback put
 * a second modal, and a second backdrop, over the first while the page
 * resolved (measured in a production build, KAN-368). One in ../@modal
 * itself would wrap the slot on every page. The section boundaries here are
 * the whole loading state.
 */
export function allSections() {
  return {
    personal: (
      <Suspense fallback={<SectionSkeleton title="Personal Details" photo />}>
        <PersonalSection />
      </Suspense>
    ),
    // Its two lists of rows, the sign-in and its methods (KAN-819): with no
    // fallback the section stood blank while it read the session, the one
    // section of the five with no skeleton. The boundary also covers the
    // notice's useSearchParams (./security/notice.tsx).
    security: (
      <Suspense
        fallback={
          <>
            <SectionSkeleton title="Sign-In" rows={2} />
            <SectionSkeleton title="Sign-In Methods" rows={2} />
          </>
        }
      >
        <SecuritySection />
      </Suspense>
    ),
    notifications: (
      <Suspense fallback={<SectionSkeleton title="Notifications" fields={2} />}>
        <NotificationsSection />
      </Suspense>
    ),
    integrations: (
      <Suspense fallback={<SectionSkeleton title="Integrations" fields={2} />}>
        <IntegrationsSection />
      </Suspense>
    ),
    preferences: (
      <Suspense fallback={<SectionSkeleton title="Job Preferences" fields={4} />}>
        <PreferencesSection />
      </Suspense>
    ),
  };
}

/**
 * A section while it reads: its card, its heading as a bar (`title` still
 * names it to a screen reader), then, for Personal Details, the photo's 72px
 * circle beside its buttons, and a field's label and 42px box for each field (`fields`), so the card
 * is about the height it will be. A section of setting rows (./setting-row.tsx,
 * Sign-In & Security) passes `rows` instead: each row's 36px glyph tile, its
 * name and value lines and its button. The modal shows one section at a time and
 * each scrolls alone, so nothing outside the card moves when it fills.
 */
export function SectionSkeleton({
  title,
  photo = false,
  fields = 3,
  rows,
}: {
  title: string;
  photo?: boolean;
  fields?: number;
  rows?: number;
}) {
  if (rows) {
    return (
      <Card as="section" aria-label={title} aria-busy="true" className="flex flex-col gap-4">
        <SectionHeadingSkeleton />
        <div aria-hidden="true" className="divide-border-subtle flex flex-col divide-y">
          {Array.from({ length: rows }, (_, i) => (
            <div key={i} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <Skeleton className="rounded-control size-9 shrink-0" />
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <Skeleton className="h-3.5 w-24" />
                <Skeleton className="h-3 w-48 max-w-full" />
              </div>
              <Skeleton className="h-9 w-24 shrink-0" />
            </div>
          ))}
        </div>
      </Card>
    );
  }
  return (
    <Card as="section" aria-label={title} aria-busy="true" className="flex flex-col gap-4">
      <SectionHeadingSkeleton />
      <div aria-hidden="true" className="flex flex-col gap-6">
        {photo && (
          <div className="flex items-center gap-4">
            <Skeleton className="size-18 shrink-0 rounded-full" />
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9 w-32" />
              <Skeleton className="h-3 w-44" />
            </div>
          </div>
        )}
        <div className="flex flex-col gap-4">
          {Array.from({ length: fields }, (_, i) => (
            <div key={i} className="flex flex-col gap-1">
              <Skeleton className="h-[18px] w-24" />
              <Skeleton className="rounded-control h-[42px] w-full" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
