import { cn } from "@/lib/cn";
import type { ReportStatus } from "@/lib/fill-reports";

/**
 * A native field in a Fill Reports form: a white box with the field edge
 * (`border-control`, 3:1), at the height of the page's buttons. The forms
 * stay native GET and action forms on purpose (`docs/design.md` lets an
 * admin form keep native fields), so they work with no script.
 */
export const FIELD =
  "border-border-control bg-panel text-body text-ink rounded-control focus-visible:ring-brand-ring h-9 border px-3 focus-visible:ring-2 focus-visible:outline-none";
export const FIELD_LABEL = "text-label text-ink-muted flex flex-col gap-1.5";

/** Each status's colours. The word says the status, so it is never colour alone. */
const STATUS_TONES: Record<ReportStatus, string> = {
  new: "bg-brand-tint text-brand-ink",
  triaged: "bg-warning-tint text-warning",
  fixed: "bg-positive-tint text-positive-ink",
};

/** A report's status as a pill: New, Triaged or Fixed. */
export function StatusPill({ status }: { status: ReportStatus }) {
  return (
    <span
      className={cn(
        "text-note rounded-full px-2 py-0.5 font-medium whitespace-nowrap",
        STATUS_TONES[status],
      )}
    >
      {status[0].toUpperCase() + status.slice(1)}
    </span>
  );
}
