"use client";

import { PlusIcon, SearchIcon } from "@/components/icons";
import { PencilLineIcon, ProhibitIcon, XIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { LightningRoundedIcon } from "@/components/custom-icons";
import { Button, ButtonLink } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { useToast } from "@/components/ui/toast";
import {
  closeRunTab,
  openNextApplication,
  showRunTab,
  useBrowserTabs,
  useClosedTabs,
} from "@/lib/autofill-extension";

import { dequeueJob, queueJob, skipJob } from "./actions";
import type { ActivityItem } from "./activity-list";
import { AddJobsDialog, type SavedJob } from "./add-jobs-dialog";
import { openedNote } from "./opened-note";
import { filterQueue, NO_QUEUE_FILTERS, QueueToolbar, type QueueFilters } from "./queue-filters";
import { useQueueGroupBy } from "./queue-layout";
import { canOpen, groupOf, QueueTable, type QueueRow } from "./queue-table";
import { ResumeDialog } from "./resume-dialog";

/**
 * Up Next (KAN-359): every job in the queue, in the order the extension
 * takes it (oldest first), with Add Jobs at the heading's right.
 *
 * **Grouped by whether WorkIt has started each job** (./queue-table.tsx):
 * In Progress (open in a batch tab, with the tab's own state, read live
 * from the extension: useBrowserTabs asks every few seconds while this
 * shows; or Needs You once its tab closed) and Queued (not started). A tab that
 * closes or sends its application refreshes the route, since its stage may
 * have moved (needs_you, applied) and only the server reads it.
 *
 * **A row's status is its one action** (`act`): a click goes to the job's
 * tab (showRunTab), opens a started job again whose tab was closed
 * (openNextApplication with its id, which fills its form again). Its ⋯ menu (./row-menu.tsx) holds
 * Change Resume, I Already Applied and Remove From Queue on every row.
 * **The Resume cell is a button** opening the row's resume picker
 * (./resume-dialog.tsx); the cell shows that pick, else the rule's
 * (./(queue)/page.tsx), and an empty Choose Resume slot when there is none.
 *
 * **Rows are picked with select boxes.** While any is picked, the heading's
 * right end shows the count and the two things to do to them, in place of
 * Add Jobs; Select All unpicks them (./queue-table.tsx):
 *
 *   Remove       `remove`, as the row menu's Remove From Queue.
 *   Auto Apply   opens the picked jobs with no tab open (queued, or started with its tab closed)
 *                in batch tabs
 *                (openNextApplication with their ids): they go first, and
 *                a batch started from them opens nothing else.
 *
 * A Stop (close a filling job's tab, so it waits again) and a Clear sat
 * there too until 2026-10-29: Stop's square read as one more select box
 * and Remove already closes the tab, and Select All clears a pick.
 *
 * **Remove works on every row** (`remove`): a tab open on it closes first;
 * a queued job leaves the queue (dequeueJob), with Undo in the toast, which
 * queues it again at the end; a started one (needs_you), which the queue's DELETE
 * refuses, is skipped (skipJob), with no Undo.
 *
 * **Add Jobs** opens the saved jobs to pick and queue (./add-jobs-dialog.tsx).
 *
 * **Notices over the queue**, in the shared amber notice
 * (components/ui/notice.tsx): written questions waiting, with Write
 * Answers (`QuestionsNotice`), and, while no Posting Closed heading gathers
 * them, the closed postings (`ClosedQueueNotice`, the Tracker's words).
 *
 * **The toolbar** (./queue-filters.tsx): search, Status, Company and Match
 * filters, All Filters and Table Settings (Group By), as every page table
 * has. The filtering is done here, on the rows this page holds.
 */
export function UpNext({ items, saved }: { items: ActivityItem[]; saved: SavedJob[] }) {
  const router = useRouter();
  const toast = useToast();
  const tabs = useBrowserTabs();
  const closedTabs = useClosedTabs();
  const [adding, setAdding] = useState(false);
  const [resumeFor, setResumeFor] = useState<ActivityItem | null>(null);
  const [picked, setPicked] = useState<ReadonlySet<string>>(new Set());
  const [filters, setFilters] = useState<QueueFilters>(NO_QUEUE_FILTERS);
  const groupBy = useQueueGroupBy();
  const [pending, start] = useTransition();
  // One action at a time: `pending` lands a render late, and a fast double press sent two requests.
  const busy = useRef(false);

  const rows: QueueRow[] = items.map((item) => {
    const tab = tabs.get(item.id) ?? null;
    const tabClosed = !tab && closedTabs.has(item.id);
    return { ...item, tab, tabClosed, group: groupOf(item, tab, tabClosed) };
  });
  // What the filter row lets through. A pick counts only while its row
  // shows, so Remove and Auto Apply never act on a hidden job.
  const shown = filterQueue(rows, filters);
  const checked = shown.filter((row) => picked.has(row.id));
  const closed = rows.filter((row) => row.group === "closed");
  const openable = checked.filter(canOpen);

  // A tab that closed or sent its application: its stage may have moved, so read the queue again.
  const seen = useRef<ReadonlyMap<string, string>>(new Map());
  useEffect(() => {
    const before = seen.current;
    seen.current = tabs;
    const left = [...before.keys()].some((id) => !tabs.has(id));
    const sent = [...tabs].some(
      ([id, state]) => state === "applied" && before.get(id) !== "applied",
    );
    if (left || sent) router.refresh();
  }, [tabs, router]);

  function once(work: () => Promise<void>) {
    if (busy.current) return;
    busy.current = true;
    start(async () => {
      try {
        await work();
      } finally {
        busy.current = false;
      }
    });
  }

  const apply = (targets: QueueRow[]) =>
    once(async () => {
      const result = await openNextApplication(targets.map((row) => row.id));
      if (result.opened) setPicked(new Set());
      const one = targets.length === 1;
      toast.show({
        message: result.opened
          ? `${one ? "It is" : `${targets.length} jobs are`} filling in background tabs, five at a time.`
          : result.reason === "queue_empty"
            ? `${one ? "It" : "None of them"} could open. ${one ? "Its posting" : "Their postings"} may have closed.`
            : openedNote(result),
      });
    });

  const remove = (targets: QueueRow[]) =>
    once(async () => {
      const results = await Promise.all(
        targets.map(async (row) => {
          if (row.tab) await closeRunTab(row.id);
          if (row.status === "failed") return { row, undo: false, ...(await skipJob(row.id)) };
          const out = await dequeueJob(row.id);
          // Its fill moved it to needs_you since the page loaded: the queue's DELETE refuses it.
          if (out.error) return { row, undo: false, ...(await skipJob(row.id)) };
          return { row, undo: true, ...out };
        }),
      );
      const removed = results.filter((result) => !result.error);
      const failed = results.length - removed.length;
      const undoable = removed.filter((result) => result.undo).map((result) => result.row);
      setPicked(new Set());
      router.refresh();
      const one = removed.length === 1 && targets.length === 1;
      toast.show({
        message: one
          ? `${targets[0].role} from ${targets[0].company} is removed from Auto Apply.`
          : `${removed.length} ${removed.length === 1 ? "job is" : "jobs are"} removed from Auto Apply.${
              failed > 0 ? ` ${failed} couldn't be removed.` : ""
            }`,
        ...(undoable.length > 0 && {
          action: {
            label: "Undo",
            onClick: async () => {
              // One at a time, so they join the queue's end in the order they had.
              let lost = 0;
              for (const row of undoable) if ((await queueJob(row.id)).error) lost += 1;
              if (lost > 0) toast.show({ message: `Couldn't put ${lost} back in the queue.` });
              router.refresh();
            },
          },
        }),
      });
    });

  /** A click on a row's status (./queue-table.tsx, Status): where the job is finished. */
  function act(row: QueueRow) {
    if (row.tab) void showRunTab(row.id);
    else apply([row]);
  }

  return (
    // No heading (2026-11-11): the Tracker and Documents open on their
    // toolbar, and "Up Next" over a page that holds only the queue said
    // nothing. The name stays for a screen reader.
    <section aria-label="Up Next" className="mt-6">
      <QueueToolbar
        rows={rows}
        filters={filters}
        onChange={setFilters}
        actions={
          checked.length > 0 ? (
            <>
              <span className="text-note text-ink tabular-nums">{checked.length} selected</span>
              {/* Text: it acts on the picked rows (frontend/docs/design.md,
                  which button look). Auto Apply is the view's one main
                  action while rows are picked, so it alone is filled. */}
              <Button variant="ghost" size="sm" disabled={pending} onClick={() => remove(checked)}>
                <XIcon aria-hidden className="size-4" />
                Remove
              </Button>
              <Button
                size="sm"
                disabled={openable.length === 0 || pending}
                onClick={() => apply(openable)}
              >
                <LightningRoundedIcon aria-hidden />
                Auto Apply
              </Button>
            </>
          ) : (
            // Filled: the page's main action, as Generate Resume is on
            // Documents. It was bordered beside the old heading.
            <Button size="sm" onClick={() => setAdding(true)}>
              <PlusIcon className="size-4" />
              Add Jobs
            </Button>
          )
        }
      />

      {/* The notices under the filters and over the table, where the
          Tracker draws its closed postings' notice. */}
      <QuestionsNotice items={items} />
      {/* The closed postings, as the Tracker's notice says its own, while
          no Posting Closed heading gathers them (Group By other than
          Status). */}
      {groupBy !== "status" && closed.length > 0 && (
        <ClosedQueueNotice
          count={closed.length}
          showing={filters.groups.length === 1 && filters.groups[0] === "closed"}
          onShow={(on) => setFilters({ ...NO_QUEUE_FILTERS, groups: on ? ["closed"] : [] })}
          onRemoveAll={() => remove(closed)}
        />
      )}

      {rows.length > 0 && shown.length === 0 ? (
        <EmptyState
          Icon={SearchIcon}
          title="No Matching Jobs"
          className="mt-4"
          action={
            <Button variant="secondary" size="sm" onClick={() => setFilters(NO_QUEUE_FILTERS)}>
              Clear Filters
            </Button>
          }
        >
          Nothing in Up Next matches these filters.
        </EmptyState>
      ) : rows.length > 0 ? (
        <QueueTable
          rows={shown}
          groupBy={groupBy}
          picked={picked}
          onPick={(ids) => setPicked(new Set(ids))}
          onAction={act}
          onResume={setResumeFor}
          onRemove={(row) => remove([row])}
          onRemoveAll={remove}
        />
      ) : (
        <EmptyState Icon={LightningRoundedIcon} title="Nothing Queued Yet" className="mt-4">
          Add Jobs from your saved ones, or click Auto Apply on any job.
        </EmptyState>
      )}

      <AddJobsDialog jobs={saved} open={adding} onOpenChange={setAdding} />
      {resumeFor && (
        <ResumeDialog
          key={resumeFor.id}
          jobId={resumeFor.id}
          role={resumeFor.role}
          company={resumeFor.company}
          current={resumeFor.resumeKey ?? null}
          open
          onOpenChange={(open) => !open && setResumeFor(null)}
        />
      )}
    </section>
  );
}

/**
 * Up Next's closed postings, in the shared notice (components/ui/notice.tsx)
 * with the Tracker's words and actions (applications/closed-saved.tsx,
 * `ClosedNotice`): Show Them (the Status filter set to Posting Closed; Show
 * All clears it) and Remove All, which has Undo, as Remove does.
 */
function ClosedQueueNotice({
  count,
  showing,
  onShow,
  onRemoveAll,
}: {
  count: number;
  showing: boolean;
  onShow: (on: boolean) => void;
  onRemoveAll: () => void;
}) {
  const jobs = count === 1 ? "job" : "jobs";
  return (
    <Notice
      Icon={ProhibitIcon}
      className="mt-4"
      actions={
        <>
          <Button variant="section" onClick={() => onShow(!showing)}>
            {showing ? "Show All" : "Show Them"}
          </Button>
          <Button variant="section" onClick={onRemoveAll} className="hover:text-danger">
            Remove All
          </Button>
        </>
      }
    >
      {showing
        ? `Showing the ${count} queued ${jobs} whose posting closed.`
        : count === 1
          ? "The posting closed for 1 queued job. It can't go out."
          : `Postings closed for ${count} queued jobs. They can't go out.`}
    </Notice>
  );
}

/**
 * Written questions waiting, as a notice over the queue, only while any
 * job has them (2026-11-10): how many, for how many jobs, and Write
 * Answers (Written Answers, ../answers). It is work a job asks for, not
 * setup, so it left the setup row (./setup-strip.tsx) after a day there;
 * as "Write 5 Questions →" in Up Next's heading before that, it read as a
 * stray link. Each job's own count stays in its Status cell.
 */
function QuestionsNotice({ items }: { items: ActivityItem[] }) {
  const waiting = items.filter((item) => (item.questions ?? 0) > 0 && !item.closed);
  const total = waiting.reduce((sum, item) => sum + (item.questions ?? 0), 0);
  if (total === 0) return null;
  return (
    <Notice
      Icon={PencilLineIcon}
      className="mt-4"
      actions={
        <ButtonLink href="/auto-apply/answers" variant="secondary" size="sm">
          Write Answers
        </ButtonLink>
      }
    >
      {total} {total === 1 ? "question" : "questions"} to write for {waiting.length}{" "}
      {waiting.length === 1 ? "job" : "jobs"} before {waiting.length === 1 ? "it goes" : "they go"}{" "}
      out.
    </Notice>
  );
}
