import { CloudSlashIcon } from "@phosphor-icons/react/ssr";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/empty-state";

import { TryAgainButton } from "./try-again";

/**
 * A read that failed (KAN-819): `EmptyState` with the cloud glyph and Try
 * Again, the one look for every failed read in the student app, a page's or
 * a card's (`compact`). The title names what did not load ("Your Answers
 * Aren't Loading Right Now"); the line says what happened and to try again,
 * never "Refresh the page", since the button is right there.
 *
 * `detail` is the API's own message, for whoever runs the app locally: pass
 * it only in development, as every caller does. `onRetry` is for a part that
 * reads in the browser; without it Try Again reads the page again on the
 * server (./try-again.tsx).
 */
export function LoadFailed({
  title,
  children,
  detail,
  onRetry,
  compact = false,
  className,
}: {
  title: string;
  children: ReactNode;
  detail?: ReactNode;
  onRetry?: () => unknown;
  compact?: boolean;
  className?: string;
}) {
  return (
    <EmptyState
      Icon={CloudSlashIcon}
      title={title}
      compact={compact}
      className={className}
      action={<TryAgainButton onRetry={onRetry} />}
      detail={detail}
    >
      {children}
    </EmptyState>
  );
}
