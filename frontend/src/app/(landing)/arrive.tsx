"use client";

import { useRef, useSyncExternalStore, type ReactNode } from "react";

import { useArrived } from "./hooks";

/**
 * Marks its box `data-arrived` "false" until it is well on screen, then
 * "true", so the CSS inside (`.journey-in`, `.journey-grow` in landing.css)
 * plays its entrance once, in time (useArrived: it resets only once the box
 * is wholly below the screen). No attribute in the server's HTML and the
 * first render, so the page shows finished without script and hydrates
 * without a mismatch.
 */
export function Arrive({ className, children }: { className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  // False on the server and while hydrating, true after: React's own way
  // to tell the two apart without a state set in an effect.
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(ref, mounted);
  return (
    <div ref={ref} className={className} data-arrived={mounted ? String(arrived) : undefined}>
      {children}
    </div>
  );
}

const noSubscribe = () => () => {};
