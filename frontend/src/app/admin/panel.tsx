import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn } from "@/lib/cn";

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
 */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  /** A note or a control for this card alone, at the title's right. */
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <Card as="section" tone="tile" padding="none" className={cn("flex flex-col", className)}>
      <div className="border-border-subtle border-b px-5 py-4">
        <SectionHeading action={action}>{title}</SectionHeading>
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
