"use client";

import type { ReactElement } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/shadcn/tooltip";

/**
 * A tooltip for a control that cannot be an `IconButton` (ui/icon-button.tsx):
 * a link, a `Button` that keeps its own look (a toolbar's ghost or secondary
 * glyph), a dialog's close, a menu item. `children` is the control itself,
 * which the tooltip's trigger renders, so no wrapper element joins the row.
 *
 * EVERY ICON-ONLY CONTROL SAYS WHAT IT IS ON HOVER (2026-11-11, the user's
 * rule): an `IconButton`, which always draws its tooltip, or this. A
 * `title` alone does not count (it shows late, and never to touch or a
 * keyboard), nor does an `aria-label` alone. The control keeps its own
 * accessible name: the tooltip is visual only.
 *
 * `disabled` stops the tooltip only, for a control that is off.
 */
export function Tip({
  label,
  side,
  disabled,
  children,
}: {
  label: string;
  side?: "top" | "bottom" | "left" | "right";
  disabled?: boolean;
  children: ReactElement;
}) {
  return (
    <Tooltip>
      <TooltipTrigger render={children} disabled={disabled} />
      <TooltipContent side={side}>{label}</TooltipContent>
    </Tooltip>
  );
}
