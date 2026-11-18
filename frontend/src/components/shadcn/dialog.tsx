"use client";

import * as React from "react";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";

import { cn } from "@/lib/cn";
import { Button } from "@/components/shadcn/button";
import { IconButton } from "@/components/ui/icon-button";
import { XIcon } from "@phosphor-icons/react/ssr";

function Dialog({ ...props }: DialogPrimitive.Root.Props) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />;
}

function DialogTrigger({ ...props }: DialogPrimitive.Trigger.Props) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />;
}

function DialogPortal({ ...props }: DialogPrimitive.Portal.Props) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />;
}

function DialogClose({ ...props }: DialogPrimitive.Close.Props) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />;
}

function DialogOverlay({ className, ...props }: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      data-slot="dialog-overlay"
      className={cn(
        "data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0 fixed inset-0 isolate z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs",
        className,
      )}
      {...props}
    />
  );
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  ...props
}: DialogPrimitive.Popup.Props & {
  showCloseButton?: boolean;
}) {
  return (
    <DialogPortal>
      <DialogOverlay />
      {/* WorkIt's: a column no taller than the window less 16px a side, so
          a `DialogBody` between the header and the footer scrolls and the
          buttons stay in view (KAN-820). shadcn's was a grid with no height
          cap, and six dialogs scrolled whole, their buttons with them. A
          dialog with no body scrolls whole, as before. */}
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        className={cn(
          "bg-popover text-popover-foreground ring-foreground/10 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-xl p-4 text-sm ring-1 duration-100 outline-none sm:max-w-sm",
          className,
        )}
        {...props}
      >
        {children}
        {showCloseButton && (
          // WorkIt's own Close, as every panel's (ui/icon-button.tsx, `place`):
          // shadcn's ghost Button here was 28px and square-cornered.
          <DialogPrimitive.Close
            data-slot="dialog-close"
            render={
              <IconButton
                place="row"
                label="Close"
                tooltip={false}
                className="absolute top-2 right-2"
              >
                <XIcon aria-hidden />
              </IconButton>
            }
          />
        )}
      </DialogPrimitive.Popup>
    </DialogPortal>
  );
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex shrink-0 flex-col gap-2", className)}
      {...props}
    />
  );
}

/**
 * WorkIt's (KAN-820): what sits between a dialog's header and its footer,
 * the one part that scrolls. It runs to the dialog's edges, so its
 * scrollbar sits at the edge, and keeps the scrollbar's room
 * (`dialog-scroller`, globals.css): 8px of room and 8px of padding make the
 * 16px the header and the footer have, so the content lines up with both.
 * On a touch screen the bar overlays and takes no room, so the padding is
 * the full 16px. 4px over and under it keep a field's focus ring at its
 * top or foot from being cut off. Its children never shrink: a child with
 * `overflow-hidden` (Home's table in its rounded frame) has no minimum
 * height in a flex column, and it shrank and cut off its rows where the
 * body should have scrolled.
 */
function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-scroller"
      className={cn(
        "-mx-4 -my-1 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-1 *:shrink-0 pointer-fine:pr-2",
        className,
      )}
      {...props}
    />
  );
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean;
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "bg-muted/50 -mx-4 -mb-4 flex shrink-0 flex-col-reverse gap-2 rounded-b-xl border-t p-4 sm:flex-row sm:justify-end",
        className,
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>Close</DialogPrimitive.Close>
      )}
    </div>
  );
}

/** WorkIt's type: `text-title`, 20px at 600 (2026-11-17). It was
 *  `text-subtitle`, 16px, from KAN-820, and over onboarding's 40px question
 *  the user found a dialog's title too small to lead it; every dialog took
 *  the larger size, so they stay one size. shadcn's was 16px medium, a
 *  pairing nothing else uses. `leading-tight`, not 1: a long title wraps
 *  (`break-words` at some call sites), and at 20px lines set solid touched. */
function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn("font-heading text-title leading-tight", className)}
      {...props}
    />
  );
}

function DialogDescription({ className, ...props }: DialogPrimitive.Description.Props) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn(
        "text-muted-foreground *:[a]:hover:text-foreground text-sm *:[a]:underline *:[a]:underline-offset-3",
        className,
      )}
      {...props}
    />
  );
}

export {
  Dialog,
  DialogClose,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
};
