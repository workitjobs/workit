import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A notice over a page's table or list: something waits on the student, in
 * one amber band, a glyph, one sentence and the actions that settle it
 * (2026-11-11). Auto Apply drew it first, for written questions waiting
 * (auto-apply/up-next.tsx, `QuestionsNotice`); the Tracker's closed
 * postings (applications/closed-saved.tsx, `ClosedNotice`) and Up Next's
 * use it too. The Tracker's was a white card with a black pill of its own
 * until then, a second look for the same job: reuse this one for any notice
 * of that kind rather than drawing another.
 *
 * The actions follow the button rule (frontend/docs/design.md): bordered
 * for one that goes somewhere new (Write Answers), text for one that acts
 * on what is shown (Show Them, Remove All). The sentence takes at least
 * 15rem; narrower, the actions take a line of their own rather than
 * squeezing it into a column. role="status": news, not an interruption.
 */
export function Notice({
  Icon,
  children,
  actions,
  className,
}: {
  Icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={cn(
        "bg-warning-tint/60 border-warning/25 rounded-card flex flex-wrap items-center gap-x-3 gap-y-2 border px-4 py-2.5",
        className,
      )}
    >
      <Icon aria-hidden className="text-warning size-4 shrink-0" />
      <p className="text-body text-ink min-w-0 flex-1 basis-60">{children}</p>
      {actions && <div className="flex shrink-0 items-center gap-4">{actions}</div>}
    </div>
  );
}
