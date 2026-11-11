"use client";

import type { ReactNode } from "react";

import { CheckIcon } from "@/components/icons";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/shadcn/dialog";
import { cn } from "@/lib/cn";

/**
 * A wait the student watches step by step: a modal with a small drawing of
 * what the wait does (`art`), a title, and the steps as a list, a check on
 * each done, a spinner on the one running and a small dot on those to come.
 * Tailor's run and Generate (KAN-444) each draw it, their steps set by what
 * the API streams, never by a timer. It cannot be closed (Esc and a click
 * outside do nothing): neither wait can be stopped.
 *
 * The list stays: one sentence over a thin four-part bar was tried for
 * Tailor on 2026-11-01, and the user wanted to watch the steps finish. What
 * went is an old list's circle on every row, an empty one and one with a
 * dot, which read as radio buttons under a spinner of their own.
 */
export function StepsDialog<S extends string>({
  open,
  title,
  art,
  steps,
  at,
}: {
  open: boolean;
  title: string;
  art: ReactNode;
  /** Every step, in order, with what the list says for it. */
  steps: Record<S, string>;
  /** The step running now. */
  at: S;
}) {
  const keys = Object.keys(steps) as S[];
  const now = keys.indexOf(at);
  return (
    <Dialog open={open}>
      <DialogContent showCloseButton={false} className="gap-0 overflow-hidden p-0 sm:max-w-sm">
        {art}
        <div className="px-6 pt-5 pb-6">
          <DialogTitle className="text-subtitle text-ink truncate text-center font-semibold">
            {title}
          </DialogTitle>
          <DialogDescription className="sr-only" role="status">
            {steps[at]}
          </DialogDescription>
          <ol role="list" className="mx-auto mt-4 flex w-fit flex-col gap-2.5">
            {keys.map((key, i) => {
              const done = i < now;
              const running = i === now;
              return (
                <li
                  key={key}
                  aria-current={running ? "step" : undefined}
                  className={cn(
                    "text-label flex items-center gap-2.5 transition-colors duration-300",
                    running ? "text-ink" : done ? "text-ink-muted" : "text-ink-meta",
                  )}
                >
                  <span aria-hidden className="flex size-4.5 shrink-0 items-center justify-center">
                    {done ? (
                      <span className="bg-brand text-on-brand animate-pop flex size-full items-center justify-center rounded-full">
                        <CheckIcon className="size-3" />
                      </span>
                    ) : running ? (
                      <span className="border-brand-tint border-t-brand size-full animate-spin rounded-full border-2" />
                    ) : (
                      <span className="bg-border-strong size-1.5 rounded-full" />
                    )}
                  </span>
                  {steps[key]}
                </li>
              );
            })}
          </ol>
        </div>
      </DialogContent>
    </Dialog>
  );
}
