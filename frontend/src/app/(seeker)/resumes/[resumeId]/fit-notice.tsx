"use client";

import { ScissorsIcon, WarningIcon, XIcon } from "@phosphor-icons/react/ssr";

import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

/**
 * A resume over one page, said once as a toast (KAN-258), with the bar's
 * Fit to One Page (`FitButton`) keeping the fix. `FitNotice`, the count and
 * Fit as one amber group, was the phone's top bar's until KAN-586 gave the
 * phone the desktop's toolbar.
 */

/**
 * The toast: when the editor opens on a resume over one page, or an edit
 * pushes one over. It says by how much and offers Fit to One Page; it closes
 * on Fit, on its cross, once the resume fits, or after 10 seconds, since the
 * bar keeps the same fix. role="status": news, not an interruption.
 */
export function FitToast({
  pages,
  linesOver,
  onFit,
  onClose,
  disabled,
  className,
}: {
  pages: number;
  linesOver: number;
  onFit: () => void;
  onClose: () => void;
  disabled: boolean;
  /** Where it sits: the corner on a desktop, above the bottom bar on a phone. */
  className?: string;
}) {
  const over =
    linesOver > 0
      ? `About ${linesOver} ${linesOver === 1 ? "line runs" : "lines run"} onto page 2.`
      : `It runs to ${pages} pages.`;

  return (
    <div
      role="status"
      className={cn(
        "bg-panel ring-border-subtle shadow-lift animate-rise rounded-card fixed z-50 flex items-start gap-3 p-4 ring-1",
        className,
      )}
    >
      <span className="bg-warning-tint text-warning flex size-9 shrink-0 items-center justify-center rounded-full">
        <WarningIcon aria-hidden className="size-4.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-body text-ink font-semibold">Over One Page</p>
        <p className="text-note text-ink-meta mt-0.5">
          {over} Fit to One Page hides the least useful lines until it fits.
        </p>
        <Button size="sm" className="mt-3" onClick={onFit} disabled={disabled}>
          <ScissorsIcon aria-hidden /> Fit to One Page
        </Button>
      </div>
      <IconButton place="row" tooltip={false} label="Dismiss" onClick={onClose}>
        <XIcon aria-hidden />
      </IconButton>
    </div>
  );
}
