import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

/** The slab's edge: this many squircles stacked behind the face, a step
 *  apart in depth, so the icon reads as a thin cube from its tilt. */
const EDGE = Array.from({ length: 12 }, (_, i) => i + 1);

/**
 * WorkIt's app icon as a thin slab of glass, floating (KAN-923, the user's
 * asks, 2026-11-20: What is WorkIt opened on a plain grey label, and a flat
 * icon still read as 2D). The face is the logo's figure (`components/
 * logo.tsx`, the geometry of `public/workit-icon.svg`) in white on a
 * frosted sheet in a violet squircle lit from above; behind it twelve
 * squircles a step apart in depth make its edge, and the whole slab is
 * tilted in 3D (`perspective` and `preserve-3d`) so the edge shows, as the
 * hiring systems' coins were built. It floats up and down on a slow loop
 * over a soft shadow on the ground that shrinks as it rises, still with
 * reduced motion. All of it is CSS and one small SVG (`.app-icon-3d` in
 * landing.css), with no image file. Decoration: the heading by it names
 * WorkIt.
 */
export function AppIcon({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn("app-icon-3d", className)}>
      <span className="app-icon-shadow" />
      <span className="app-icon-float">
        <span className="app-icon-slab">
          {EDGE.map((n) => (
            <span key={n} className="app-icon-edge" style={{ "--n": n } as CSSProperties} />
          ))}
          <span className="app-icon app-icon-face">
            <svg viewBox="0 0 100 100" className="app-icon-glyph">
              <defs>
                <linearGradient id="workit-app-icon-glyph" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="white" />
                  <stop offset="1" stopColor="white" stopOpacity="0.8" />
                </linearGradient>
              </defs>
              <path
                d="M23.15 40.25 L36.58 69.65 L50 49.84 L63.42 69.65 L76.85 40.25"
                fill="none"
                stroke="url(#workit-app-icon-glyph)"
                strokeWidth={8.31}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx={50} cy={33.22} r={7.03} fill="white" />
            </svg>
          </span>
        </span>
      </span>
    </span>
  );
}
