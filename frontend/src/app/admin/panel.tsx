import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn } from "@/lib/cn";

import { type AdminSection, SECTION_TARGET } from "./pages";

/**
 * An admin page's titled card (KAN-879): WorkIt's `Card` with its title, a
 * `SectionHeading`, over a rule, then the body. Every section of an admin
 * page is one, 16px from the next.
 *
 * It is the `tile` tone, as Home's sections and the stat tiles beside it
 * are: no outline, set apart by `--shadow-tile`, the 20px corner. It was the
 * default card (an outline over `--shadow-panel`, a 1px halo), so on one
 * page the tiles stood up from the ground and the cards under them lay
 * flat, and the user asked for a shadow on every box.
 *
 * It takes its `section` from `./pages.ts`, never a title of its own: the
 * section's label is the card's title and its id is the card's, so the
 * sidebar's link to the section says the same words and always has a
 * target.
 */
export function Panel({
  section,
  action,
  children,
  className,
  bodyClassName,
}: {
  section: AdminSection;
  /** A note or a control for this card alone, at the title's right. */
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  const titleId = `${section.id}-title`;
  return (
    <Card
      as="section"
      tone="tile"
      padding="none"
      id={section.id}
      aria-labelledby={titleId}
      className={cn("flex flex-col", SECTION_TARGET, className)}
    >
      <div className="border-border-subtle border-b px-5 py-4">
        <SectionHeading id={titleId} action={action}>
          {section.label}
        </SectionHeading>
      </div>
      <div className={cn("flex-1 p-5", bodyClassName)}>{children}</div>
    </Card>
  );
}

/** A table header cell in an admin card. */
export const TH = "text-label text-ink-meta px-5 py-3";
/** A table body cell in an admin card. */
export const TD = "px-5 py-3";

/** The admin pages' frame: WorkIt's page width and gutters, 24px under the top. */
export const ADMIN_FRAME = "max-w-dashboard mx-auto w-full px-4 py-6 sm:px-6 lg:px-8";
