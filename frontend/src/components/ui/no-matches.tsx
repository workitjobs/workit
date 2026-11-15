import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * The line a picker shows when its search or filters leave no row (KAN-819):
 * a resume picker, Pick an Application, the editor's Experiences picker. One
 * size for all of them: they came in four, 12px and 14px, with 0, 8px and
 * 24px around them. A whole list or page with nothing to show is an
 * `EmptyState`; this is for a list inside a dialog or a panel.
 *
 * A status, so a screen reader hears the list empty out as the student types.
 */
export function NoMatches({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p role="status" className={cn("text-body text-ink-meta py-3", className)}>
      {children}
    </p>
  );
}
