import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * An empty slot in an application's section card: the place a sent resume,
 * the answers or an event fills, as one quiet line with its glyph, the
 * height of a resume row so nothing jumps when one arrives. What You Sent
 * (./your-application.tsx) and Interviews & Dates (./tracker-controls.tsx)
 * both draw it inside their white card (KAN-824): Interviews & Dates had a
 * bare line on the grey ground instead.
 */
export function EmptySlot({
  icon,
  className,
  children,
}: {
  icon: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex min-h-13 items-center gap-2", className)}>
      {icon}
      <p className="text-body text-ink-meta">{children}</p>
    </div>
  );
}
