import type { Ref } from "react";

import { cn } from "@/lib/cn";

import { Button } from "./button";

/**
 * The two answers to a question asked before a delete (KAN-817): **Keep
 * It** first, the red button last, in every shape the question takes. A
 * dialog's footer (`DeleteDialog`, the Tracker's Remove), a popover
 * (`DeleteResumeConfirm`), a bar across a dialog's foot (`ConfirmBar`,
 * Settings' `DiscardBar`) and Settings' Delete Account step all draw their
 * buttons with it, so the order and the words cannot drift. A line under
 * the thing (`DeleteConfirm`) was one more shape until KAN-818 gave its one
 * use, Written Answers' Remove, an Undo instead.
 *
 * Until then the question came in four shapes and the red button moved
 * sides: first in the popover, the line and Delete Account, last in the
 * dialogs and the bars, so on Resumes deleting one resume and deleting
 * several put Delete on opposite sides. The way out said Keep It in four
 * places, Cancel in three and Keep My Account in one. A student who learns
 * "the safe answer is on the left" now finds it there every time, and a
 * dialog's first focus lands on it, not on the delete.
 *
 * - `act` names what the red button does to what: "Delete Resume", "Remove
 *   3", "Clear All". Never "OK", "Yes" or "Confirm" (design.md: a button
 *   names its action).
 * - `keep` is "Keep It" for every delete. "Keep Editing" is the one other
 *   answer, for Discard Your Changes?, where nothing is deleted yet and "Keep
 *   It" would not say what is kept. The type allows nothing else.
 * - `busy` holds both buttons while the delete runs and says "Deleting…" on
 *   the red one, so a second press cannot send a second delete.
 * - `disabled` holds the red button alone until the question is answered
 *   (Delete Account waits for the typed email).
 *
 * The pair stays one row at every width, right-aligned where its box is
 * wider than the buttons (a dialog's footer on a phone); a container that
 * places it left (a Settings step, a line of text) keeps it left. A dialog's
 * Keep It closes it through `onKeep`, so the caller's own close (a state
 * set, an unmount) is the only one.
 */
export function ConfirmButtons({
  act,
  keep = "Keep It",
  size,
  busy = false,
  disabled = false,
  keepRef,
  onKeep,
  onAct,
  className,
}: {
  /** The red button's words: "Delete Resume". */
  act: string;
  keep?: "Keep It" | "Keep Editing";
  /** `sm` in a popover or on a line; a dialog, a bar or a step keeps the default. */
  size?: "sm" | "default";
  busy?: boolean;
  disabled?: boolean;
  /** For a bar that takes the focus on Keep It as it opens. */
  keepRef?: Ref<HTMLButtonElement>;
  onKeep: () => void;
  onAct: () => void;
  className?: string;
}) {
  return (
    <div className={cn("flex shrink-0 justify-end gap-2", className)}>
      <Button ref={keepRef} size={size} variant="secondary" onClick={onKeep} disabled={busy}>
        {keep}
      </Button>
      <Button size={size} variant="destructive" onClick={onAct} disabled={busy || disabled}>
        {busy ? "Deleting…" : act}
      </Button>
    </div>
  );
}
