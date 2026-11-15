"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/button";

/**
 * Try Again on a failed read (KAN-819), the one way on that `LoadFailed`
 * offers. With no `onRetry` it asks the server for the page again
 * (`router.refresh()`), which runs every server read once more and keeps the
 * address, the query and an open Settings modal as they are; a full reload
 * of a Settings section's address would have dropped the page behind the
 * modal for Home. A part that reads in the browser passes its own read as
 * `onRetry`. It reads "Loading…" and takes no second click until the read is
 * done (docs/design.md, "Every control has all its states").
 */
export function TryAgainButton({ onRetry }: { onRetry?: () => unknown }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      variant="secondary"
      size="sm"
      disabled={pending}
      onClick={() =>
        startTransition(async () => {
          if (onRetry) await onRetry();
          else router.refresh();
        })
      }
    >
      {pending ? "Loading…" : "Try Again"}
    </Button>
  );
}
