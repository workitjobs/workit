import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import "./grid-frame.css";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

/**
 * The frame for a page that stands outside both shells and the marketing
 * site: the marketing pages' drafting grid round one column (2026-11-22,
 * KAN-935; it replaced a grey card, on some pages over a violet skyline).
 * A white page; the top row with the logo, a link to the home page, in
 * the marketing header's box; the foot row with the year, Privacy and
 * Terms; and from lg up the grid's two rails where the home page's stand,
 * a hairline under the top row and one over the foot row, and an ink
 * square at every crossing. Below lg there are no lines. A page puts an
 * `AuthCard` (auth-card.tsx) in it.
 *
 * **Two shapes.** With a `scene` (the auth screens, auth-frame.tsx) the
 * frame is two halves: the page in the left one, the scene in the right
 * one. With none (/uninstalled, /coming-soon) the page stands in the
 * middle two of the home hero's four columns, with a divider at each side
 * of that cell. **A scene goes beside a sign-in step only**: the product's
 * pictures beside "why did you remove WorkIt?" would be noise.
 *
 * **It stands still and loads no marketing stylesheet**: the entrance is
 * the auth frame's, which marks it `auth-enter` and loads landing.css. So
 * a page's button in the plain frame is the app's `Button`, and its
 * heading is Plus Jakarta Sans only where the page passes that font's
 * variable in `className`.
 *
 * **It is a whole page, so the 404 cannot use it**: Next draws
 * `not-found.tsx` inside the layout the 404 happened under, and there
 * this frame put a second logo row inside the marketing page. The 404
 * draws one cell of the grid instead (app/not-found.tsx).
 */
export function GridFrame({
  className,
  scene,
  children,
}: {
  /** On the frame's root: a font's variable, `auth-enter`. */
  className?: string;
  /** The right half, from lg up. Decoration: it is hidden from assistive
   *  technology, so it holds no link and nothing the page needs. */
  scene?: ReactNode;
  children: ReactNode;
}) {
  const at = (x: number): CSSProperties => ({ left: `${x}%` });
  return (
    <div className={cn("relative flex flex-1 flex-col bg-white", className)}>
      {/* The top row's foot line, the rails through it and their two
          squares are its own, so they move with it when it drops in. */}
      <header className="grid-bar relative shrink-0">
        <div className="relative mx-auto flex h-[4.5rem] w-full max-w-6xl items-center px-4 sm:h-[4.75rem] sm:px-6 lg:px-8">
          <Link href="/" aria-label="WorkIt home" className="flex h-11 items-center">
            <Logo size="card" decorative />
          </Link>
          <span aria-hidden="true" className="grid-bar-marks">
            <span className="left-0" />
            <span className="right-0" />
            <i className="left-0" />
            <i className="left-full" />
          </span>
        </div>
        <span aria-hidden="true" className="grid-bar-line" />
      </header>

      <div className="relative mx-auto w-full max-w-6xl flex-1 px-6 lg:grid lg:grid-cols-4 lg:px-2">
        {/* The page is centred in its cell's height (the user's call,
            2026-11-22: hung from the top, it read as stuck there). `safe`:
            a column taller than the cell starts at its top instead of
            spilling above it. */}
        <main
          className={cn(
            "lg:col-span-2 lg:flex lg:flex-col lg:justify-center-safe",
            !scene && "lg:col-start-2",
          )}
        >
          {children}
        </main>

        {/* `.landing` gives a scene the marketing tokens it is drawn with
            (the frame that passes one loads landing.css). */}
        {scene && (
          <div aria-hidden="true" className="landing relative hidden lg:col-span-2 lg:block">
            {scene}
          </div>
        )}
      </div>

      <footer className="text-ink-meta relative mx-auto flex h-14 w-full max-w-6xl shrink-0 items-center justify-between px-4 text-sm sm:px-6 lg:px-8">
        <p>© {new Date().getFullYear()} WorkIt</p>
        <p className="flex gap-5">
          <Link href="/privacy" className="hover:text-ink transition-colors">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-ink transition-colors">
            Terms
          </Link>
        </p>
      </footer>

      {/* Last, so the rails draw over a scene's white ground. With a
          scene, the square at the right rail's foot is the scene's own
          (a cell's handle, auth-frame.tsx). */}
      <span aria-hidden="true" className="grid-lines">
        <span className="grid-foot" />
        <span className="grid-rails">
          <span className="left-0" />
          <span className="right-0" />
          {!scene && [25, 75].map((x) => <span key={x} className="cut" style={at(x)} />)}
          {!scene && [25, 75].map((x) => <i key={x} className="top" style={at(x)} />)}
          {(scene ? [0] : [0, 25, 75, 100]).map((x) => (
            <i key={x} style={at(x)} />
          ))}
        </span>
      </span>
    </div>
  );
}
