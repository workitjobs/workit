"use client";

import { useState, type ReactNode } from "react";

import { TableSettingsIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/cn";

/** The trigger's look while a setting differs from the table's default and
 *  the menu is closed, as a filter dropdown takes it with a pick. */
const IN_USE = "border-brand bg-brand-tint text-brand hover:bg-brand-tint";

/**
 * A page table's Table Settings (2026-11-10, after Notion's table toolbar):
 * a round icon button, sliders (`TableSettingsIcon`), at the right end of
 * the table's filter row beside All Filters (components/filter-actions.tsx),
 * over a menu titled Table Settings. Every table with a filter row has one,
 * the Tracker's list and Auto Apply's Up Next, and each fills it with its
 * own settings, each group under its own label: Group By on both
 * (`GroupByOptions`), and the Tracker's columns. A pick leaves the menu
 * open for the next.
 *
 * `inUse` tints the button, the cue that the table is not as it starts
 * (the Tracker: hidden columns); `label` is its name for a screen reader
 * when it says more than "Table Settings".
 */
export function TableSettingsMenu({
  label = "Table Settings",
  inUse = false,
  className,
  children,
}: {
  label?: string;
  inUse?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      {/* An IconButton, so it says "Table Settings" on hover (2026-11-11; it
          had only a `title`, which touch and keyboard never see). */}
      <DropdownMenuTrigger
        render={
          <IconButton
            variant="soft"
            label={label}
            tooltip="Table Settings"
            className={cn("size-9 shrink-0", inUse && !open && IN_USE, className)}
          >
            <TableSettingsIcon className="size-4" />
          </IconButton>
        }
      />
      <DropdownMenuContent align="end" className="w-max min-w-52">
        <p className="text-label text-ink px-2 pt-1.5 pb-1 font-semibold">Table Settings</p>
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Group By: how the table puts its rows under headings, one of `options`
 *  (Status first, None last), radio rows that leave the menu open. */
export function GroupByOptions<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <DropdownMenuGroup>
      <DropdownMenuLabel>Group By</DropdownMenuLabel>
      <DropdownMenuRadioGroup value={value} onValueChange={(next) => onChange(next as T)}>
        {options.map((option) => (
          <DropdownMenuRadioItem key={option.value} value={option.value} closeOnClick={false}>
            {option.label}
          </DropdownMenuRadioItem>
        ))}
      </DropdownMenuRadioGroup>
    </DropdownMenuGroup>
  );
}
