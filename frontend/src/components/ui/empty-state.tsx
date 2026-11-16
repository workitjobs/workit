import type { ComponentType, ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

/**
 * What a screen shows in place of content it doesn't have: nothing to list
 * yet, or a load that failed. One shape for both, so a failed fetch reads as
 * a calm, finished part of the page rather than a stray line of red text, and
 * an empty list says what will fill it instead of leaving a blank.
 *
 * `detail` is for the reader who can act on the cause — the raw API message
 * during development, say. The `title` and `children` are always for the
 * seeker, so they never carry instructions like "run the scraper".
 *
 * role="status" rather than "alert": by the time this renders the page has
 * finished loading, and nothing here is urgent enough to interrupt a screen
 * reader mid-sentence.
 *
 * The title may break mid-word, because a caller can echo user input in it
 * (/search puts the query there): an unbroken one, a pasted URL say, would
 * otherwise widen the card past a phone's screen and scroll the page sideways.
 *
 * `titleAs` is h1 where the state is the whole view, a 404 under a section
 * whose bar title is then a plain line; an h2 under the page's h1 otherwise.
 *
 * `compact` is the same look for a state inside a card, a tile or a dialog
 * that already has its own edge and heading (KAN-819): no card of its own, a
 * smaller glyph tile, the title as a 14px line rather than a heading (the
 * card's own heading names the section), and a 12px line under it. Settings'
 * sections, Home's tiles and Application Info's cards draw their failed reads
 * this way, so a failed card reads as the page's failed read in small.
 */
export function EmptyState({
  Icon,
  title,
  children,
  detail,
  action,
  titleAs,
  compact = false,
  className,
}: {
  Icon: ComponentType<{ className?: string }>;
  title: string;
  children?: ReactNode;
  detail?: ReactNode;
  action?: ReactNode;
  titleAs?: "h1" | "h2" | "p";
  compact?: boolean;
  className?: string;
}) {
  if (compact) {
    const Title = titleAs ?? "p";
    return (
      <div
        role="status"
        className={cn("flex flex-col items-center px-4 py-6 text-center", className)}
      >
        <span className="bg-brand-tint text-brand rounded-control flex size-8 items-center justify-center">
          <Icon aria-hidden className="size-4" />
        </span>
        <Title className="text-body text-ink mt-2 max-w-full font-semibold break-words">
          {title}
        </Title>
        {children && <p className="text-note text-ink-meta mt-0.5 max-w-sm">{children}</p>}
        {action && <div className="mt-3">{action}</div>}
        {detail && <p className="text-note text-ink-meta mt-2 max-w-sm">{detail}</p>}
      </div>
    );
  }
  const Title = titleAs ?? "h2";
  return (
    <Card
      role="status"
      padding="none"
      elevated={false}
      className={cn("flex flex-col items-center px-6 py-10 text-center", className)}
    >
      <span className="bg-brand-tint text-brand rounded-control flex size-10 items-center justify-center">
        <Icon aria-hidden className="size-5" />
      </span>
      <Title className="text-subtitle text-ink mt-3 max-w-full break-words">{title}</Title>
      {children && <p className="text-body text-ink-meta mt-1 max-w-md">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
      {detail && <p className="text-note text-ink-meta mt-3 max-w-md">{detail}</p>}
    </Card>
  );
}
