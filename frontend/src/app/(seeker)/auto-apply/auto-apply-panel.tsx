import type { ReactNode } from "react";

/**
 * The top of the Auto Apply page: `children` is the page's sections, the
 * setup strip and Up Next (./(queue)/page.tsx). The queue's line ("3 in
 * progress · 2 queued") sat here, alone above the setup strip, until
 * 2026-11-10; it is beside Up Next's heading now (./up-next.tsx).
 *
 * NO BUTTON IN THE HEADER. Start Auto Apply sat at its top right until it
 * was dropped (asked for 2026-10-29): the app's page headers hold a view
 * switcher there, not a primary action. It queued the seeker's 10 best
 * matches (POST .../auto-apply/batches) and then opened the queue; its
 * Pause and Resume only moved a state of its own. Jobs now join the queue
 * from their own Auto Apply button or Up Next's Add Jobs, and open from Up
 * Next, where the student picks them and presses Auto Apply (./up-next.tsx).
 * Before it, Manage Resumes and Add to Claude sat here too (KAN-424): each
 * queued row shows and changes its own resume, and the setup strip
 * (./setup-strip.tsx) offers what a batch still needs.
 */
export function AutoApplyPanel({ children }: { children: ReactNode }) {
  // The page's padding is the first section's top margin.
  return <div className="[&>:first-child]:mt-0">{children}</div>;
}
