"use client";

import Link from "next/link";
import { useEffect, useRef, type ComponentType, type MouseEvent, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type SideNavItem = {
  key: string;
  label: string;
  href: string;
  Icon: ComponentType<{ className?: string }>;
};

/**
 * A page's own menu of its parts, each with its own address (2026-11-11,
 * from Settings' menu): a column beside the part from `sm`, every item a
 * glyph and a label, the open one in the brand tint, the rest muted ink
 * that fills grey under the pointer; on a phone, a row that scrolls
 * sideways above the part, since long labels do not fit equal widths.
 * Used by Settings (settings/settings-nav.tsx, which switches its part in
 * place with `onSelect`) and Application Info (auto-apply/info, whose
 * parts are pages, so a plain link). The column stays put while the part
 * scrolls (`sticky`), so a menu never leaves the screen.
 *
 * `head` sits above the items in the column, in their look (Application
 * Info's "Auto Apply" way back).
 */
export function SideNav({
  label,
  items,
  active,
  onSelect,
  head,
  className,
}: {
  /** The menu's name for a screen reader. */
  label: string;
  items: readonly SideNavItem[];
  active: string;
  /** A plain click switches the part in place, with no navigation; a
   *  modified click still opens the address in a new tab. */
  onSelect?: (key: string) => void;
  head?: ReactNode;
  className?: string;
}) {
  const current = useRef<HTMLAnchorElement>(null);

  // On a phone the row scrolls sideways, and a part near its end opened out
  // of view.
  useEffect(() => {
    current.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [active]);

  return (
    // min-w-0: in a grid or flex row the menu would grow to its row's full
    // width on a phone, and the page, not the row, scrolled sideways.
    <nav aria-label={label} className={cn("min-w-0 sm:sticky sm:top-6 sm:self-start", className)}>
      {head}
      <ul className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 sm:mx-0 sm:flex-col sm:overflow-visible sm:px-0">
        {items.map(({ key, label: name, href, Icon }) => {
          const isCurrent = key === active;
          const select = onSelect
            ? (event: MouseEvent) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                onSelect(key);
              }
            : undefined;
          return (
            <li key={key} className="shrink-0">
              <Link
                href={href}
                ref={isCurrent ? current : undefined}
                aria-current={isCurrent ? "page" : undefined}
                onClick={select}
                className={cn(SIDE_NAV_ITEM, isCurrent ? SIDE_NAV_CURRENT : SIDE_NAV_IDLE)}
              >
                <Icon className="size-4 shrink-0" />
                {name}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** An item's look, for a row drawn in the menu's place (`head`). */
export const SIDE_NAV_ITEM =
  "rounded-control text-label focus-visible:ring-brand-ring flex items-center gap-2 px-3 py-2 whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none";
const SIDE_NAV_CURRENT = "bg-brand-tint text-brand font-semibold";
export const SIDE_NAV_IDLE = "text-ink-muted hover:bg-hover hover:text-ink";
