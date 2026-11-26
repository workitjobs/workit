"use client";

import Link from "next/link";
import { useState, type ComponentProps } from "react";

/**
 * A link that prefetches only once the pointer moves over it, the focus
 * reaches it, or a finger touches it, never because it scrolled into view
 * (KAN-916). Next's own pattern (its prefetching guide, "Hover-triggered
 * prefetch"), with one change: a pointer that has not moved does not count.
 *
 * FOR A LIST OF JOB LINKS. A job page has a loading.tsx, so Next prefetches
 * each job link in view down to it, and that prefetch runs the page's
 * generateMetadata, which reads GET /jobs/{id}: about 100 API calls for a
 * Jobs page of 50 cards, once production stopped keeping that read (its
 * data cache is off, frontend/open-next.config.ts). Prefetched on intent,
 * the click still finds the skeleton ready: a hover leads a click by about
 * a quarter of a second, and a touch fires before the tap's click.
 *
 * MOVEMENT, NOT MOUSEENTER. When a filter change draws new cards under a
 * resting pointer, the browser sends mouseenter to each card that passes
 * under it, and four prefetches followed every change on 2026-11-18. Such
 * an event moves nothing (movementX and movementY are 0), so only a
 * pointer the student moves counts.
 */
export function HoverPrefetchLink({
  onPointerMove,
  onFocus,
  onTouchStart,
  ...props
}: Omit<ComponentProps<typeof Link>, "prefetch">) {
  const [wanted, setWanted] = useState(false);
  return (
    <Link
      {...props}
      // null is Next's default prefetch, set once the student shows intent.
      prefetch={wanted ? null : false}
      onPointerMove={(event) => {
        if (!wanted && (event.movementX !== 0 || event.movementY !== 0)) setWanted(true);
        onPointerMove?.(event);
      }}
      onFocus={(event) => {
        setWanted(true);
        onFocus?.(event);
      }}
      onTouchStart={(event) => {
        setWanted(true);
        onTouchStart?.(event);
      }}
    />
  );
}
