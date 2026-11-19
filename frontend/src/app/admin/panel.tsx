import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

/**
 * An admin page's titled card (KAN-879): the title, and any control for the
 * card, over a rule, then the body. Every section of an admin page is one.
 */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  /** A control for this card alone, at the title's right: a filter, a note. */
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <Card as="section" padding="none" className={cn("flex flex-col", className)}>
      <header className="border-border-subtle flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
        <h2 className="text-ink text-base font-semibold">{title}</h2>
        {action}
      </header>
      <div className={cn("flex-1 p-5", bodyClassName)}>{children}</div>
    </Card>
  );
}

/** A table header cell in an admin card: small capitals, as the cards' labels. */
export const TH = "text-caption text-ink-meta px-5 py-3 uppercase";
/** A table body cell in an admin card. */
export const TD = "px-5 py-3.5";
