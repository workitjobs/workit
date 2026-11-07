"use client";

import { useState, type ReactElement, type ReactNode, type RefObject } from "react";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/shadcn/popover";
import { Button } from "@/components/ui/button";

/**
 * A delete's question on a line under what it deletes: what goes and what
 * stays, then the red Delete and Keep It. The answer bank's Delete asks here
 * (`auto-apply/answers/delete-answer.tsx`). The bank's entries and Clear All
 * asked here too, until KAN-732 moved them into `DeleteDialog`, below. A
 * resume asks in `DeleteResumeConfirm`, below, with the same words and
 * buttons.
 *
 * The two buttons wrap as one group: wrapped one by one, Keep It sat alone
 * on a line under Delete Resume. `busy` holds Delete while the request runs,
 * so a second press cannot send a second delete.
 */
export function DeleteConfirm({
  label,
  busy = false,
  onDelete,
  onKeep,
  children,
}: {
  /** The red button's words, "Delete Resume". */
  label: string;
  busy?: boolean;
  onDelete: () => void;
  onKeep: () => void;
  /** The question: what goes, and what stays. */
  children: ReactNode;
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
      <span className="text-note text-ink-muted">{children}</span>
      <div className="flex gap-2">
        <Button size="sm" variant="destructive" onClick={onDelete} disabled={busy}>
          {label}
        </Button>
        <Button size="sm" variant="secondary" onClick={onKeep}>
          Keep It
        </Button>
      </div>
    </div>
  );
}

/**
 * A delete's question in a modal (KAN-732): Delete Entry on Experiences and
 * in onboarding's resume preview, and Experiences' Clear All. It asked on a
 * line under the editor (`DeleteConfirm`), which a long editor opened out of
 * view, which took no focus and which a screen reader never heard. Drawn as
 * the app's other questions are (`company/jobs/close-job-dialog.tsx`): the
 * question names what goes, the line under it what goes with it and what
 * stays, then Keep It and the red button.
 *
 * Open while mounted: the caller mounts it to ask and unmounts it on Keep It
 * or once the delete is done. Escape, a press outside and the × are Keep It,
 * except while the delete runs (`busy`). Focus starts on Keep It, the safe
 * answer, and Keep It gives it back to the control that opened the question.
 * A failed delete keeps the question open with the error in it.
 */
export function DeleteDialog({
  title,
  label,
  busy = false,
  error,
  onDelete,
  onKeep,
  children,
}: {
  /** The question: "Delete Treasurer?" */
  title: string;
  /** The red button's words: "Delete Entry". */
  label: string;
  busy?: boolean;
  /** Why the delete failed. */
  error?: string | null;
  onDelete: () => void;
  onKeep: () => void;
  /** What goes with it, and what stays. */
  children: ReactNode;
}) {
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onKeep();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-subtitle font-semibold break-words">{title}</DialogTitle>
          <DialogDescription>{children}</DialogDescription>
        </DialogHeader>
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <DialogFooter>
          <DialogClose render={<Button variant="secondary">Keep It</Button>} />
          <Button variant="destructive" onClick={onDelete} disabled={busy}>
            {label}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Delete's confirm on a resume (KAN-347): a popover hung from the control
 * that opened it, a card's trash or the upload page's Delete, so the
 * question sits where the student clicked. Under the card it opened below
 * the row's notes, away from the icon, and pushed the rows under it down.
 * Every resume's Delete asks here, so the cards and the upload page stay
 * alike. Escape or a click outside is Keep It. It stays open while the
 * delete runs, with Delete Resume held (`busy`): a deleted resume's row
 * takes it away, and a failed one closes it so the error under the row
 * shows.
 *
 * A phone's card picks Delete from its More menu (`RowMoreMenu`, KAN-575):
 * that menu passes no `trigger` but `open` and `anchor`, and the popover
 * hangs from the menu's button and gives the focus back to it.
 */
export function DeleteResumeConfirm({
  trigger,
  anchor,
  open: shown,
  onOpenChange,
  busy = false,
  onDelete,
}: {
  /** The button the popover hangs from. */
  trigger?: ReactElement;
  /** With no trigger: what the popover hangs from, and `open` says when. */
  anchor?: RefObject<HTMLElement | null>;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  busy?: boolean;
  onDelete: () => Promise<void>;
}) {
  const [own, setOwn] = useState(false);
  const open = shown ?? own;
  const setOpen = onOpenChange ?? setOwn;

  async function remove() {
    await onDelete();
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      {trigger && <PopoverTrigger render={trigger} />}
      <PopoverContent
        anchor={anchor}
        finalFocus={anchor}
        align="end"
        className="w-auto max-w-72 gap-3"
      >
        <p className="text-note text-ink-muted text-pretty">
          Delete this resume? Files you already sent are kept.
        </p>
        <div className="flex gap-2">
          <Button size="sm" variant="destructive" onClick={remove} disabled={busy}>
            Delete Resume
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setOpen(false)}>
            Keep It
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
