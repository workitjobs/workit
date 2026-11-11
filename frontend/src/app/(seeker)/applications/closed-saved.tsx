"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { TrashIcon } from "@/components/icons";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { IconButton } from "@/components/ui/icon-button";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";

import type { Application } from "../tracker";
import { applicationsHref } from "./query";
import { useApplicationsQuery } from "./view-switcher";
import { unsaveJob } from "../jobs/actions";

/**
 * In place of the stage menu on a closed saved job (`isClosedSaved` in
 * ../tracker.ts, 2026-11-05): a muted
 * "Posting closed", which says why the row's logo is grey, and a trash
 * button that takes the job out of the Tracker.
 *
 * The words carry the meaning, not the grey: colour alone fails WCAG 1.4.1,
 * and a screen reader never hears a faded logo. So the button's name repeats
 * the reason ("Remove Product Designer at Triumph, posting closed").
 *
 * IT ASKS FIRST. The API saves only an open job, so a closed one could not
 * be saved again: there is no Undo to offer, and the app asks first wherever
 * it has none (as the stage menu does before leaving Saved).
 */
export function ClosedSavedControl({
  app,
  className,
}: {
  app: Pick<Application, "id" | "role" | "company">;
  className?: string;
}) {
  const router = useRouter();
  const toast = useToast();
  const [asking, setAsking] = useState(false);
  const [pending, start] = useTransition();

  function remove() {
    setAsking(false);
    start(async () => {
      const { error } = await unsaveJob(app.id);
      if (error) {
        toast.show({ message: `Couldn't remove ${app.role}. ${error}` });
        return;
      }
      toast.show({ message: `Removed ${app.role}.` });
      router.refresh();
    });
  }

  return (
    <div className={cn("flex items-center justify-between gap-2", className)}>
      {/* The stage pill's shape and size, so the Status column keeps one
          shape down the table, in solid ink (2026-11-10, the user's call):
          grey, it read as Saved beside Saved's grey pill, and red would
          read as Rejected. No stage is black, so a closed posting stands
          out as the end of the road. */}
      <span className="bg-ink text-on-inverse text-label rounded-full px-2.5 py-1 font-medium whitespace-nowrap">
        Posting Closed
      </span>
      <IconButton
        label={`Remove ${app.role} at ${app.company}, posting closed`}
        tooltip="Remove"
        disabled={pending}
        onClick={() => setAsking(true)}
      >
        <TrashIcon className="size-4" />
      </IconButton>
      <Dialog open={asking} onOpenChange={setAsking}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-subtitle font-semibold">Remove {app.role}?</DialogTitle>
            <DialogDescription>
              Its posting at {app.company} has closed, so you can&apos;t save it again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="secondary">Cancel</Button>} />
            <Button variant="destructive" onClick={remove}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * The saved jobs whose postings closed, as a notice over the table, only
 * while there are any (2026-11-10): how many, **Show Them** (?closed=1, the
 * table with those alone; Show All undoes it) and **Remove All**, which asks
 * first, as one row's trash does, since a closed job cannot be saved again.
 * They were scattered through the table, each found by its row, and taken
 * out one at a time. A group pinned to the table's top or foot was weighed
 * and left: it would fight the columns' sort.
 */
export function ClosedNotice({ apps }: { apps: Pick<Application, "id" | "role">[] }) {
  const query = useApplicationsQuery();
  const router = useRouter();
  const toast = useToast();
  const [asking, setAsking] = useState(false);
  const [pending, start] = useTransition();
  const count = apps.length;
  const jobs = count === 1 ? "job" : "jobs";

  function removeAll() {
    setAsking(false);
    start(async () => {
      const results = await Promise.all(apps.map((app) => unsaveJob(app.id)));
      const failed = results.filter((result) => result.error).length;
      toast.show({
        message:
          failed === 0
            ? `Removed ${count} closed ${jobs}.`
            : `Removed ${count - failed}. ${failed} couldn't be removed.`,
      });
      router.push(applicationsHref(query, { closed: false }), { scroll: false });
      router.refresh();
    });
  }

  return (
    <Card
      padding="none"
      role="status"
      className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5"
    >
      <span className="bg-ink text-on-inverse text-note shrink-0 rounded-full px-2 py-0.5 font-medium">
        Posting Closed
      </span>
      {/* At least 15rem: narrower, the buttons take a line of their own
          rather than squeezing the words into a column. */}
      <p className="text-body text-ink min-w-0 flex-1 basis-60">
        {query.closed
          ? `Showing the ${count} saved ${jobs} whose posting closed.`
          : count === 1
            ? "The posting closed for 1 saved job. You can no longer apply to it."
            : `Postings closed for ${count} saved jobs. You can no longer apply to them.`}
      </p>
      <div className="flex items-center gap-4">
        <Link
          href={applicationsHref(query, { closed: !query.closed })}
          scroll={false}
          className={buttonClasses({ variant: "section" })}
        >
          {query.closed ? "Show All" : "Show Them"}
        </Link>
        <Button
          variant="section"
          disabled={pending}
          onClick={() => setAsking(true)}
          className="hover:text-danger"
        >
          Remove All
        </Button>
      </div>
      <Dialog open={asking} onOpenChange={setAsking}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-subtitle font-semibold">
              Remove {count} closed {jobs}?
            </DialogTitle>
            <DialogDescription>
              Their postings have closed, so you can&apos;t save them again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="secondary">Cancel</Button>} />
            <Button variant="destructive" onClick={removeAll}>
              Remove {count}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
