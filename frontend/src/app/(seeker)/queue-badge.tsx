"use client";

import { useEffect, useRef, useState, useSyncExternalStore, useTransition } from "react";

import { readQueueCount } from "./auto-apply/actions";
import { readStageChanges, subscribeStageChanges } from "./jobs/shown-list";

const noChanges = () => null;

/**
 * The count on the sidebar's Auto Apply row (2026-11-09): how many jobs wait
 * in the queue, queued and needs-you alike. It is the queue's one status
 * outside the Auto Apply page, on every page and in both of the Jobs page's
 * views, at no cost in layout: a right column beside the Jobs page's cards
 * was tried the same day and taken out (docs/auto_apply_in_jobs.md).
 *
 * The layout reads the count on the server (`initial`). A card's Auto Apply,
 * Save or Undo never reloads the page; each writes the tab's stage changes
 * (./jobs/shown-list, rememberStage), so the badge reads the count again
 * whenever those change after it was drawn. Nothing shows at zero, or when
 * the count can't be read.
 */
export function QueueBadge({ initial }: { initial: number | null }) {
  const [count, setCount] = useState(initial);
  const [, startTransition] = useTransition();
  const changes = useSyncExternalStore(subscribeStageChanges, readStageChanges, noChanges);
  const first = useRef(changes);

  useEffect(() => {
    // The changes already there when the page drew are in `initial`.
    if (changes === first.current) return;
    startTransition(async () => {
      setCount(await readQueueCount());
    });
  }, [changes]);

  if (!count) return null;
  return (
    <span className="bg-brand text-on-brand text-meta flex h-4.5 min-w-4.5 items-center justify-center rounded-full px-1 leading-none font-semibold tabular-nums">
      {count > 99 ? "99+" : count}
      <span className="sr-only"> {count === 1 ? "job" : "jobs"} in the queue</span>
    </span>
  );
}
