"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * One of the time control's two arrows (KAN-879), a link whether it can
 * move or not.
 *
 * ONE ELEMENT IN BOTH STATES. Where the window cannot move the arrow was a
 * plain `<a>` with no address, and a `Link` otherwise: two element types in
 * one place, so React removed the node as an arrow reached its limit, and a
 * keyboard's focus fell to the page's start (WCAG 2.4.3). It is now always
 * the same `Link`. Off, it is `aria-disabled`, points at the window in view
 * and stops its own click, so focus stays on it and a screen reader hears
 * its new name. A client part only for that click guard.
 */
export function WindowArrow({
  href,
  label,
  off,
  children,
}: {
  /** The window's address; the one in view when `off`. */
  href: string;
  /** "Show Oct 26 to Nov 8", or "No Earlier Days" when `off`. */
  label: string;
  off: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-label={label}
      aria-disabled={off || undefined}
      onClick={off ? (event) => event.preventDefault() : undefined}
      className={cn(
        "border-border-surface bg-panel focus-visible:ring-brand-ring inline-flex size-8 shrink-0 items-center justify-center rounded-full border focus-visible:ring-2 focus-visible:outline-none",
        off ? "text-ink-subtle cursor-default" : "text-ink hover:bg-hover",
      )}
    >
      {children}
    </Link>
  );
}
