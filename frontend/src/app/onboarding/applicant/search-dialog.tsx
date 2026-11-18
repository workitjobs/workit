"use client";

import { useState, type ComponentProps } from "react";

import { SearchPicker } from "@/components/filter-controls";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/shadcn/dialog";
import { SearchIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { RemovableChip } from "@/components/ui/chip";
import { cn } from "@/lib/cn";

type PickerProps = Pick<
  ComponentProps<typeof SearchPicker>,
  "label" | "placeholder" | "empty" | "options" | "values" | "onChange" | "create"
>;

/**
 * EVERY LONG LIST IN ONBOARDING IS SEARCHED IN A DIALOG (2026-11-17): a
 * button on the page, and what is picked beside it as chips, each with its
 * cross. On the page a search's dropdown opened over the footer, and the
 * room `SearchPicker` made for it (its lift) made the page scroll, which the
 * user found annoying: first on Role's other roles, then on Where's
 * Location. A new search on an onboarding page uses this, never a dropdown.
 *
 * The list is open from the start and fills the dialog, scrolling inside
 * it (`SearchPicker`'s `inline`), as a phone's picker is: a collapsed field
 * that unfolded into the dialog's empty room read as odd.
 */
export function SearchDialog({
  button,
  title,
  description,
  className,
  ...picker
}: PickerProps & {
  /** The button's words ("Search All Roles"). */
  button: string;
  title: string;
  description: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const nameOf = (value: string) => picker.options.find((o) => o.value === value)?.label ?? value;
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger
          render={
            <Button variant="secondary">
              <SearchIcon />
              {button}
            </Button>
          }
        />
        <DialogContent className="h-[min(40rem,calc(100dvh-2rem))] overflow-hidden sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>
          <div className="flex min-h-0 flex-1 flex-col">
            <SearchPicker inline size="lg" {...picker} />
          </div>
          <DialogFooter>
            <Button onClick={() => setOpen(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {picker.values.map((value) => (
        <RemovableChip
          key={value}
          removeLabel={`Remove ${nameOf(value)}`}
          onRemove={() => picker.onChange(picker.values.filter((v) => v !== value))}
        >
          {nameOf(value)}
        </RemovableChip>
      ))}
    </div>
  );
}
