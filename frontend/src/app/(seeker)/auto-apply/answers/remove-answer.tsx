"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

import { deleteAnswer } from "./actions";

/**
 * One answer in Your Answers (KAN-369), with Remove under it: the student's
 * own (a Looks right or Save for next time in a batch tab), one pasted with
 * Check and Save, or their Claude's. Not own limits reuse, not removal.
 * `children` are the question, the answer and its named fact, drawn on the
 * server.
 *
 * **Remove waits on its toast** (KAN-818), as Application Info's Transcript
 * does (KAN-562): the answer leaves the list at once and a toast offers
 * Undo, but the DELETE (deleteAnswer) is sent only when the toast closes
 * without it (`onClose`). Undo can't save the answer again: a save runs the
 * checks again and makes it the student's own, so Undo is the DELETE never
 * sent. It said Delete and asked first on the line under the answer until
 * then, where Writing Samples and the Transcript say Remove and offer Undo.
 * Once sent, the route refreshes so the server draws the list without it.
 * Later forms no longer fill it; a question the tab still asks comes back
 * above, unanswered, for their Claude or for them. A failed DELETE shows
 * the answer again and says why in a toast. Leaving the page sends it at
 * once.
 */
export function RemovableAnswer({
  jobId,
  name,
  children,
}: {
  jobId: string;
  name: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const toast = useToast();
  const [removed, setRemoved] = useState(false);
  // The toast whose close sends the held DELETE; null once it is sent or taken back.
  const held = useRef<number | null>(null);

  // Leaving the page sends a held DELETE at once: back here, the answer it removes would show.
  useEffect(
    () => () => {
      if (held.current !== null) toast.dismiss(held.current);
    },
    [toast],
  );

  function remove() {
    if (held.current !== null) return;
    setRemoved(true);
    const id = toast.show({
      message: "Your answer is removed. Later forms won't fill it.",
      action: {
        label: "Undo",
        onClick: () => {
          held.current = null;
          setRemoved(false);
        },
      },
      onClose: () => {
        if (held.current !== id) return;
        held.current = null;
        void send();
      },
    });
    held.current = id;
  }

  async function send() {
    const { error } = await deleteAnswer(jobId, name).catch(() => ({
      error: "Could not reach the server.",
    }));
    if (error) {
      setRemoved(false);
      toast.show({ message: `Your answer wasn't removed. ${error}` });
      return;
    }
    router.refresh();
  }

  if (removed) return null;
  return (
    <div className="flex flex-col gap-1.5">
      {children}
      <dd>
        <Button variant="section" onClick={remove}>
          Remove
        </Button>
      </dd>
    </div>
  );
}
