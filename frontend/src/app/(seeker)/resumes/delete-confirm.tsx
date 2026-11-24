"use client";

import { useState, type ReactElement, type ReactNode, type RefObject } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/shadcn/popover";
import { ConfirmButtons } from "@/components/ui/confirm-buttons";
import { Tip } from "@/components/ui/tip";

/**
 * A delete's question in a modal (KAN-732): on Experiences, Skills' Clear
 * All and a Lines section's Delete Section, which sit on the page. Delete
 * Entry, a section's Clear All and an Entries section's Delete Section ask
 * across their dialog's foot since KAN-740 (`ConfirmBar` in
 * `experiences/entry-dialog.tsx`), since a modal over a dialog is a dialog
 * over a dialog. Delete Entry asked on a line under the inline editor
 * before KAN-732, which a long editor opened out of view, which took no focus and which a screen reader never heard. Drawn as
 * the app's other questions are (`company/jobs/close-job-dialog.tsx`): the
 * question names what goes, the line under it what goes with it and what
 * stays, then Keep It and the red button (`ConfirmButtons`).
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
          <DialogTitle className="break-words">{title}</DialogTitle>
          <DialogDescription>{children}</DialogDescription>
        </DialogHeader>
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <DialogFooter>
          <ConfirmButtons act={label} busy={busy} onKeep={onKeep} onAct={onDelete} />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Delete's confirm on a resume (KAN-347): a popover hung from the control
 * that opened it, a card's trash or the upload page's Delete, so the
 * question sits where the student clicked. Keep It comes first and Delete
 * Resume last, as in the dialog that deletes several (`ConfirmButtons`,
 * KAN-817): the popover had Delete first, so the red button changed sides
 * on one page. Under the card it opened below
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
  tip,
  anchor,
  open: shown,
  onOpenChange,
  busy = false,
  onDelete,
}: {
  /** The button the popover hangs from. */
  trigger?: ReactElement;
  /** Its tooltip, for a trigger whose word folds away (an icon alone). */
  tip?: string;
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
      {trigger &&
        (tip ? (
          <Tip label={tip}>
            <PopoverTrigger render={trigger} />
          </Tip>
        ) : (
          <PopoverTrigger render={trigger} />
        ))}
      <PopoverContent
        anchor={anchor}
        finalFocus={anchor}
        align="end"
        className="w-auto max-w-72 gap-3"
      >
        <p className="text-note text-ink-muted text-pretty">
          Delete this resume? Files you already sent are kept.
        </p>
        <ConfirmButtons
          size="sm"
          act="Delete Resume"
          busy={busy}
          onKeep={() => setOpen(false)}
          onAct={remove}
        />
      </PopoverContent>
    </Popover>
  );
}
