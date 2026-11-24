import { LightningRoundedIcon } from "@/components/custom-icons";
import { Badge } from "@/components/ui/badge";

/**
 * "Auto Apply" in a job card's badge row (2026-11-09): this job posting's
 * form is one Auto Apply can fill, so a student scanning the feed sees which
 * jobs take one click. It names a fact, never a stage: the card is not drawn
 * again when its Auto Apply button queues the job, so "Queued" here would go
 * stale. It shows on exactly the cards that show the Auto Apply button, in
 * the brand tint with the button's own lightning, so the two read as one
 * feature: the badge to scan by, the button to act. It replaced a grey line
 * of text, "Auto Apply ready", at the action row's left end.
 */
export function AutoApplyChip() {
  return (
    <Badge tone="brand">
      <span className="flex items-center gap-1">
        <LightningRoundedIcon aria-hidden className="size-3.5" />
        Auto Apply
      </span>
    </Badge>
  );
}
