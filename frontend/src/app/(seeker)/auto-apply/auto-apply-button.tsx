"use client";

import { AppWindowIcon } from "@phosphor-icons/react/ssr";
import { LightningRoundedIcon } from "@/components/custom-icons";
import { useRef, useState, useTransition } from "react";

import { CheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { openNextApplication, showRunTab, useBrowserJobs } from "@/lib/autofill-extension";

import { hasApplied } from "../applied";
import { rememberStage } from "../jobs/shown-list";
import { dequeueJob, queueJob, type ApplicationStage, type RunStage } from "./actions";
import { openedNote } from "./opened-note";

/** Taking a queued job out, by one name wherever it shows: the Queued
 *  toggle's hover, the combined Apply button's menu (../jobs/
 *  apply-split-button.tsx) and Up Next's ⋯ and pick bar (KAN-818). */
export const REMOVE_FROM_QUEUE = "Remove From Queue";

/** What the button says once the job posting has an application. */
const STAGE_LABEL: Record<RunStage, string> = {
  queued: "Queued",
  needs_you: "Needs You",
  skipped: "Skipped",
  applied: "Applied",
};

/**
 * A job posting's "Auto Apply", on its card and its own page, between Ask
 * Scout and Apply Now: Ask Scout's secondary design, with the sidebar's Auto
 * Apply glyph. A click queues the job posting through the API (./actions,
 * queueJob), and the Auto Apply page lists it in Live Activity.
 *
 * `stage` is the application the server read as it drew the page (null:
 * none). A saved job (its Save button, KAN-261) counts as none: a click
 * queues it. With one, the button names its stage. Queued is a toggle: a second
 * click is Remove From Queue, the one name it has everywhere (KAN-818): it
 * takes the job out of the queue (dequeueJob) and the button reads Auto
 * Apply again. Any later stage is off: needs you, skipped and applied
 * are what happened, not a plan, so the button never undoes them. A stale
 * `stage` is harmless: a click answers the real one.
 *
 * Both ways raise a toast (components/ui/toast.tsx) with Undo, so neither
 * asks first (docs/design.md, "A write that cannot be taken back asks first
 * or offers Undo"). Queueing says "<title> from <company> is queued for Auto
 * Apply.", and its Undo takes the job out again (dequeueJob). Removing says
 * "<title> from <company> is removed from the queue.", as Up Next's Remove
 * does, and its Undo queues it again (queueJob), at the queue's end. Only a
 * new queueing raises one; a click that finds an earlier stage just shows it.
 * Each toast closes the job's last one (`say`): a queued toast left beside
 * the removal offered an Undo that could only fail.
 *
 * Every stage it sets goes to the shown list (`rememberStage`, KAN-217), so
 * the job's other buttons and every list follow: a saved job queued here
 * empties its bookmark and comes back to the Jobs page.
 *
 * THEN THE SAME PIPELINE AS START AUTO APPLY, without the matching: a click
 * that leaves the job queued asks the extension to open the oldest queued
 * job in its background tab beside this one (openNextApplication). That is
 * this job only when nothing older waits. The job open there reads Working
 * in Browser, on every card that shows it (useBrowserJobs), and a click
 * switches to that tab instead of taking the job out of the queue. The
 * opening runs after the click settles, so the button never waits on a
 * page load; only a failure shows (no extension stays silent: most
 * visitors have none).
 */
/** What a job's Auto Apply knows and does, shared by AutoApplyButton and the
 *  Jobs page's combined Apply button (../jobs/apply-split-button.tsx), so
 *  the two queue, take out, toast and open the extension's tab the same way.
 *  `done` is a stage past queued (Needs You, Skipped, Applied): what
 *  happened, not a plan, so nothing undoes it. */
export function useAutoApply({
  jobId,
  title,
  company,
  stage: initial,
}: {
  jobId: string;
  title: string;
  company: string;
  stage: ApplicationStage | null;
}) {
  const toast = useToast();
  // A stage after applied (interviewing, offer, rejected; KAN-413) reads
  // as Applied here: the button only says whether auto apply has it.
  const [stage, setStage] = useState<RunStage | null>(
    hasApplied(initial) ? "applied" : initial === "saved" ? null : initial,
  );
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  // One click at a time: `disabled={pending}` lands a render late, so a
  // fast double click queued twice, raising two toasts and two opens.
  const busy = useRef(false);
  // This job's last toast: a new one closes it, so a queued toast's Undo
  // never shows beside the removal it would contradict.
  const shown = useRef<number | null>(null);
  const inBrowser = useBrowserJobs().has(jobId);

  /** The queueing toast's Undo. A failure (a fill that began meanwhile)
   *  says so in a toast and leaves the button Queued. */
  async function undo() {
    const result = await dequeueJob(jobId);
    if (result.error) {
      toast.show({ message: `Couldn't take ${title} out of the queue. ${result.error}` });
      return;
    }
    setStage(null);
    rememberStage(jobId, null);
  }

  /** The removal toast's Undo: the job joins the queue again, at its end. A
   *  failure says so in a toast and leaves the button at Auto Apply. */
  async function requeue() {
    const result = await queueJob(jobId);
    if (!result.stage) {
      toast.show({ message: `Couldn't put ${title} back in the queue. ${result.error}` });
      return;
    }
    setStage(hasApplied(result.stage) ? "applied" : result.stage);
    rememberStage(jobId, result.stage);
  }

  /** "<title> from <company> <said>" in a toast with Undo, the job's
   *  names in medium, in place of this job's last toast. */
  function say(said: string, onUndo: () => Promise<void>) {
    if (shown.current !== null) toast.dismiss(shown.current);
    shown.current = toast.show({
      message: (
        <>
          <span className="font-medium">{title}</span> from{" "}
          <span className="font-medium">{company}</span> {said}
        </>
      ),
      action: { label: "Undo", onClick: onUndo },
    });
  }

  /** The tab opens in the background; only a failure is worth a line. */
  async function openInBrowser() {
    const result = await openNextApplication();
    if (!result.opened && (result.reason === "signed_out" || result.reason === "error")) {
      setError(openedNote(result));
    }
  }

  const queued = stage === "queued";

  /** Queues the job, or takes a queued one out: Queued is a toggle. */
  function toggle() {
    if (busy.current) return;
    busy.current = true;
    start(async () => {
      try {
        if (queued) {
          const result = await dequeueJob(jobId);
          setError(result.error);
          if (result.error) return;
          setStage(null);
          rememberStage(jobId, null);
          say("is removed from the queue.", requeue);
          return;
        }
        const result = await queueJob(jobId);
        setError(result.error);
        if (!result.stage) return;
        // The job may have moved past applied in another tab since
        // this page was drawn; it reads as Applied, as on first draw.
        setStage(hasApplied(result.stage) ? "applied" : result.stage);
        // Every other button for this job follows (KAN-217): a saved
        // job's bookmark empties once it is queued.
        rememberStage(jobId, result.stage);
        if (result.stage === "queued") {
          void openInBrowser();
          say("is queued for Auto Apply.", undo);
        }
      } finally {
        busy.current = false;
      }
    });
  }

  return {
    stage,
    queued,
    /** Queued and open in the extension's tab right now. */
    inBrowser: queued && inBrowser,
    done: stage != null && stage !== "queued" ? STAGE_LABEL[stage] : null,
    pending,
    error,
    toggle,
    goToTab: () => void showRunTab(jobId),
  };
}

export function AutoApplyButton(props: {
  jobId: string;
  title: string;
  company: string;
  stage: ApplicationStage | null;
}) {
  const auto = useAutoApply(props);

  if (auto.done) {
    return (
      <Button variant="secondary" size="sm" disabled>
        <CheckIcon className="size-4" />
        {auto.done}
      </Button>
    );
  }

  if (auto.inBrowser) {
    return (
      <Button variant="secondary" size="sm" title="Go to the tab" onClick={auto.goToTab}>
        <AppWindowIcon aria-hidden className="size-4" />
        Working in Browser
      </Button>
    );
  }

  return (
    <>
      {auto.error && (
        <p role="alert" className="text-note text-ink-meta">
          {auto.error}
        </p>
      )}
      <Button
        variant="secondary"
        size="sm"
        disabled={auto.pending}
        // A toggle: pressed while queued, and the hover says what a click does.
        aria-pressed={auto.queued}
        title={auto.queued ? REMOVE_FROM_QUEUE : undefined}
        onClick={auto.toggle}
      >
        {auto.queued ? (
          <CheckIcon className="size-4" />
        ) : (
          <LightningRoundedIcon aria-hidden className="size-4" />
        )}
        {auto.queued ? STAGE_LABEL.queued : "Auto Apply"}
      </Button>
    </>
  );
}
