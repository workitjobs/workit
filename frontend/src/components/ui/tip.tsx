"use client";

import type { ReactElement } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/shadcn/tooltip";

/**
 * A tooltip for a control that cannot be an `IconButton` (ui/icon-button.tsx):
 * a link, a `Button` that keeps its own look (a toolbar's ghost or secondary
 * glyph), a dialog's close, a menu item. `children` is the control itself,
 * which the tooltip's trigger renders, so no wrapper element joins the row.
 *
 * AN ICON-ONLY CONTROL SAYS WHAT IT IS ON HOVER UNLESS ITS GLYPH IS READ ON
 * SIGHT (2026-11-12, the user's rule; docs/design.md, Components, lists
 * both kinds): Close, Back, ⋯, Undo, a Previous arrow and the like get no
 * tooltip, since on every icon they flickered across close rows. A `title`
 * alone does not count (it shows late, and never to touch or a keyboard).
 * The control keeps its own accessible name either way: the tooltip is
 * visual only.
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
