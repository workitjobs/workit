"use client";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";

/** What the Resumes page found a resume the student already has for: a
 *  Generate that would print the same as `name`, or an upload whose text
 *  `name` already has. */
export type Duplicate = { kind: "generate" | "upload"; name: string };

/**
 * The modal for a resume the student already has (KAN-267), reworded as an
 * "Are you sure?" (KAN-444, the user's calls of 2026-11-10). It said only
 * the API's "Duplicate Resume found: <name>" with OK, which flagged the
 * copy but did not say what it meant or let the student go on.
 *
 * - **Generate**: "<name> has the same content." Confirm makes the copy
 *   anyway (`onConfirm`, Generate with `allow_duplicate`); Cancel makes
 *   nothing. A copy is cheap and edits on its own, so the student decides.
 * - **Upload**: "Your upload <name> has the same text." with OK. An
 *   upload stays refused: the database keeps one upload per text
 *   (`resumes_text_hash_key`), and a copy would take one of the 5 slots.
 *
 * Open while `duplicate` is set.
 */
export function DuplicateResumeDialog({
  duplicate,
  onConfirm,
  onClose,
}: {
  duplicate: Duplicate | null;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const generate = duplicate?.kind === "generate";
  return (
    <Dialog open={duplicate != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-subtitle font-semibold">
            You Already Have This Resume
          </DialogTitle>
          <DialogDescription>
            {generate
              ? `${duplicate.name} has the same content. Confirm to make a copy anyway.`
              : `Your upload ${duplicate?.name ?? ""} has the same text.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          {generate ? (
            <>
              <DialogClose render={<Button variant="secondary">Cancel</Button>} />
              <Button onClick={onConfirm}>Confirm</Button>
            </>
          ) : (
            <DialogClose render={<Button>OK</Button>} />
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
