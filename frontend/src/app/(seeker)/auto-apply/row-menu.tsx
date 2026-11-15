"use client";

import { FileTextIcon, XIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EllipsisIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";

import { ApplyDialog } from "../jobs/apply-button";
import { STAGE_ICON } from "../stage-colors";
import type { ActivityItem } from "./activity-list";
import { REMOVE_FROM_QUEUE } from "./auto-apply-button";

/**
 * Up Next's ⋯ on each row (KAN-424), in its own column: the row's rarer
 * actions, worded, in one menu, the same three on every row so none goes
 * missing. Going to a row's tab is not here: its Next Step button (Go to
 * Tab, Review, Finish) already does it.
 * It replaced two bare icon buttons side by side (a briefcase for "I
 * submitted this", a cross for Remove), which no one could read at 16px and
 * which put the destructive one next to the other, one slip apart:
 *
 *   Change Resume        the row's resume picker (./resume-dialog.tsx), as
 *                        its Resume cell opens
 *   I Already Applied    an application the student sent that the
 *                        extension didn't see. It opens Did You Apply?
 *                        (`ApplyDialog`, ../jobs/apply-button.tsx), as a job
 *                        card's ⋯ does (../jobs/job-more-menu.tsx), so it
 *                        asks first and keeps the resume they sent
 *                        (KAN-818); it marked the job at once, with no
 *                        resume and no Undo, until then. Yes marks it
 *                        applied, the row leaves Up Next on the refresh,
 *                        and the Tracker shows it Applied.
 *   Remove From Queue    destructive, last, on every row (`onRemove`,
 *                        ./up-next.tsx): a queued job leaves the queue with
 *                        Undo, a started one whose tab closed is skipped, and one open
 *                        in a tab has its tab closed first.
 *
 * Its rows are the menu's own (no padding or type of their own), with ink
 * glyphs, as the job card's ⋯ and a resume row's ⋯ draw theirs.
 *
 * The row leaves a click on a button or a menu item alone, and any click
 * from outside it, as this menu's portal and the dialog's are
 * (components/clickable-row.tsx), so neither opening the menu, an item nor
 * the dialog opens the job posting: each item did until KAN-566.
 */
export function RowMenu<T extends ActivityItem>({
  item,
  onResume,
  onRemove,
}: {
  item: T;
  onResume: (item: T) => void;
  onRemove: (item: T) => void;
}) {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  const Applied = STAGE_ICON.applied;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <IconButton place="row" label={`More actions for ${item.role}`} tooltip={false}>
              <EllipsisIcon />
            </IconButton>
          }
        />
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={() => onResume(item)}>
            <FileTextIcon aria-hidden className="text-ink size-4" />
            Change Resume
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setAsking(true)}>
            <Applied className="text-ink size-4" />I Already Applied
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onClick={() => onRemove(item)}>
            <XIcon aria-hidden className="size-4" />
            {REMOVE_FROM_QUEUE}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ApplyDialog
        jobId={item.id}
        title={item.role}
        open={asking}
        onOpenChange={setAsking}
        onApplied={() => {
          setAsking(false);
          router.refresh();
        }}
      />
    </>
  );
}
