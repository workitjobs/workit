"use client";

import { AppWindowIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { LightningRoundedIcon } from "@/components/custom-icons";
import { CheckIcon, ChevronDownIcon, ExternalLinkIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

import { useAutoApply } from "../auto-apply/auto-apply-button";
import type { ApplicationStage } from "../auto-apply/actions";
import { ApplyDialog } from "./apply-button";

/**
 * One Apply for a job Auto Apply can fill (2026-11-09, after Simplify's):
 * a split button whose main part is Auto Apply and whose arrow opens both
 * ways to apply, each with a line on what it does. It replaced an Auto Apply
 * button beside Apply Now, two buttons for one decision.
 *
 * THE MAIN PART IS ALWAYS AUTO APPLY, the user's choice over a default that
 * followed whether the extension is installed: it promotes the feature, and
 * a student with no extension queues a job that fills once they install it.
 * It is the brand fill while it can act, and steps down to the secondary
 * look once Auto Apply has the job (Queued, Working in Browser) or is done
 * with it (Needs You, Skipped, Applied), the states AutoApplyButton shows,
 * from the same hook (useAutoApply). Queued stays a toggle.
 *
 * APPLY MANUALLY is a link that opens the employer's posting in a new tab,
 * from the click itself so no popup blocker stops it, and opens "Did You
 * Apply?" behind it, as Apply Now does (./apply-button.tsx). A job Auto
 * Apply cannot fill keeps the plain Apply Now.
 */
export function ApplySplitButton({
  jobId,
  title,
  company,
  applyUrl,
  stage,
  canMarkApplied = false,
  applied = false,
  onApplied,
  className,
}: {
  jobId: string;
  title: string;
  company: string;
  applyUrl: string;
  stage: ApplicationStage | null;
  canMarkApplied?: boolean;
  applied?: boolean;
  onApplied?: () => void;
  className?: string;
}) {
  const router = useRouter();
  const auto = useAutoApply({ jobId, title, company, stage });
  const [asking, setAsking] = useState(false);
  // Acting: Auto Apply can still take the job. Otherwise it has it, or is
  // done with it, and the main part says which.
  const acting = !auto.done && !auto.queued;
  const variant = acting ? "default" : "secondary";

  function marked() {
    setAsking(false);
    if (onApplied) return onApplied();
    router.refresh();
  }

  const main = auto.done ? (
    <Button variant="secondary" size="sm" disabled segment="start">
      <CheckIcon className="size-4" />
      {auto.done}
    </Button>
  ) : auto.inBrowser ? (
    <Button
      variant="secondary"
      size="sm"
      title="Go to the tab"
      onClick={auto.goToTab}
      segment="start"
    >
      <AppWindowIcon aria-hidden className="size-4" />
      Working in Browser
    </Button>
  ) : (
    <Button
      variant={variant}
      size="sm"
      disabled={auto.pending}
      aria-pressed={auto.queued}
      title={auto.queued ? "Remove from the queue" : undefined}
      onClick={auto.toggle}
      segment="start"
    >
      {auto.queued ? (
        <CheckIcon className="size-4" />
      ) : (
        <LightningRoundedIcon aria-hidden className="size-4" />
      )}
      {auto.queued ? "Queued" : "Auto Apply"}
    </Button>
  );

  return (
    <>
      {auto.error && (
        <p role="alert" className="text-note text-ink-meta">
          {auto.error}
        </p>
      )}
      <div className={cn("inline-flex shrink-0", className)}>
        {main}
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Ways to apply"
            render={
              <Button
                variant={variant}
                size="sm"
                segment="end"
                className={cn(
                  // A hairline between the two parts: white on the brand
                  // fill, the edge's own grey on the secondary look.
                  acting
                    ? "shadow-[inset_1px_0_0_rgb(255_255_255/0.3)]"
                    : "shadow-[inset_1px_0_0_var(--color-border-surface)]",
                )}
              />
            }
          >
            <ChevronDownIcon className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 p-1.5">
            {!auto.done && (
              <DropdownMenuItem
                onClick={auto.toggle}
                className="items-start gap-3 rounded-md px-3 py-2.5"
              >
                <LightningRoundedIcon aria-hidden className="text-brand mt-0.5 size-4" />
                <span className="flex flex-col gap-0.5">
                  <span className="text-body text-ink font-medium">
                    {auto.queued ? "Remove from Auto Apply" : "Auto Apply"}
                  </span>
                  <span className="text-label text-ink-meta">
                    {auto.queued
                      ? "Take this job out of the queue."
                      : "WorkIt fills out the application in Chrome. You review it and submit."}
                  </span>
                </span>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              render={<a href={applyUrl} target="_blank" rel="noopener noreferrer" />}
              onClick={() => {
                if (canMarkApplied && !applied) setAsking(true);
              }}
              className="items-start gap-3 rounded-md px-3 py-2.5"
            >
              <ExternalLinkIcon className="text-ink mt-0.5 size-4" />
              <span className="flex flex-col gap-0.5">
                <span className="text-body text-ink font-medium">Apply Manually</span>
                <span className="text-label text-ink-meta">
                  Open the application site and apply yourself.
                </span>
              </span>
              <span className="sr-only"> (opens in a new tab)</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <ApplyDialog
        jobId={jobId}
        title={title}
        open={asking}
        onOpenChange={setAsking}
        onApplied={marked}
      />
    </>
  );
}
