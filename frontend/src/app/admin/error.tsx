"use client";

import { CloudSlashIcon } from "@phosphor-icons/react/ssr";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

import { ADMIN_FRAME } from "./panel";

/**
 * What an admin page shows when its read fails (KAN-879), as the seeker
 * shell's own error page does: the sidebar stays, and only the page area is
 * replaced. `retry` reads the page again on the server, which a failed API
 * call needs. A client component, as every error boundary must be.
 */
export default function AdminError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className={ADMIN_FRAME}>
      <EmptyState
        Icon={CloudSlashIcon}
        title="This Page Isn't Loading Right Now"
        action={
          <Button variant="secondary" size="sm" onClick={() => retry()}>
            Try Again
          </Button>
        }
      >
        The API did not answer. Try again, or come back in a moment.
      </EmptyState>
    </main>
  );
}
