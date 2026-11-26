"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

/** How long a list waits before it says it is still working. */
const LATE_AFTER_MS = 5000;

/**
 * A sentence a list's loading state adds once the wait runs long (KAN-916):
 * a skeleton alone held for 49 seconds once and never said the page was
 * still working. Best Match says what it is doing, since scoring every job
 * is what makes it slow; the rest only that it is still loading. A live
 * region, so a screen reader hears it too. Drawn after LATE_AFTER_MS, never
 * on a quick load.
 */
export function StillLoading({ match, className }: { match: boolean; className?: string }) {
  const [late, setLate] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setLate(true), LATE_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);
  return (
    <p role="status" className={cn("text-body text-ink-meta", !late && "sr-only", className)}>
      {late
        ? match
          ? "Still scoring jobs against your experiences. This can take up to a minute."
          : "Still loading jobs. This is taking longer than usual."
        : ""}
    </p>
  );
}
