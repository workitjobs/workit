"use client";

import { CheckCircleIcon, ExportIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EllipsisIcon } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { useToast } from "@/components/ui/toast";

import { ApplyDialog } from "./apply-button";

/**
 * A job's "⋯" (2026-11-09, after Simplify's): the actions a student needs
 * now and then, kept out of the action row.
 *
 *   Already Applied?  "Did You Apply?" (./apply-button.tsx), for a job the
 *                     student applied to elsewhere: it marks the job applied
 *                     with the resume they sent. Only for a signed-in
 *                     applicant who has not marked it already.
 *   Share             the device's share sheet where there is one, else the
 *                     job's link copied, with a toast.
 *
 * Not here yet: Report This Job Posting, which needs somewhere to store a
 * report (a table and an endpoint), and Hide This Job, which waits on
 * Not Interested being stored (NOT_INTERESTED_LIVE). A menu row that does
 * nothing is a dead button.
 *
 * The trigger is a bare glyph (IconButton's `glyph` look, with its "More
 * actions" tooltip): it sits on a white card or header, and a circle with
 * an edge is only for the grey ground. Its hover disc stays while the menu
 * is open.
 */
export function JobMoreMenu({
  jobId,
  title,
  company,
  canMarkApplied = false,
  applied = false,
  onApplied,
}: {
  jobId: string;
  title: string;
  company: string;
  canMarkApplied?: boolean;
  applied?: boolean;
  onApplied?: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const [asking, setAsking] = useState(false);
  const askable = canMarkApplied && !applied;

  function marked() {
    setAsking(false);
    if (onApplied) return onApplied();
    router.refresh();
  }

  async function share() {
    const url = `${window.location.origin}/jobs/${encodeURIComponent(jobId)}`;
    const text = `${title} at ${company}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: text, url });
        return;
      } catch (error) {
        // Closing the sheet is the student's choice, not a failure.
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.show({ message: "Link copied." });
    } catch {
      toast.show({ message: "Couldn't copy the link." });
    }
  }

  return (
    <>
      <DropdownMenu>
        {/* An IconButton with no tooltip: "⋯" reads as more on sight
            (components/ui/tip.tsx, 2026-11-12). z-2: over a card's click
            layer (components/job-posting-card.tsx). */}
        <DropdownMenuTrigger
          render={
            <IconButton
              variant="glyph"
              label={`More for ${title}`}
              tooltip={false}
              className="z-2 shrink-0"
            >
              <EllipsisIcon className="size-4" />
            </IconButton>
          }
        />
        <DropdownMenuContent align="end" className="w-56 p-1.5">
          {askable && (
            <DropdownMenuItem
              onClick={() => setAsking(true)}
              className="text-body text-ink gap-2.5 rounded-md px-3 py-2"
            >
              <CheckCircleIcon aria-hidden className="text-ink-muted size-4" />
              Already Applied?
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={() => void share()}
            className="text-body text-ink gap-2.5 rounded-md px-3 py-2"
          >
            <ExportIcon aria-hidden className="text-ink-muted size-4" />
            Share
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {askable && (
        <ApplyDialog
          jobId={jobId}
          title={title}
          open={asking}
          onOpenChange={setAsking}
          onApplied={marked}
        />
      )}
    </>
  );
}
