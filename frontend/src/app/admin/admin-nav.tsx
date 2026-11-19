"use client";

import {
  ArrowLeftIcon,
  BugBeetleIcon,
  HeartbeatIcon,
  PulseIcon,
  SidebarSimpleIcon,
} from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

/** The admin pages, in the sidebar's order. A new admin page joins this list. */
const PAGES = [
  { href: "/admin/scrape-health", label: "Scrape Health", icon: PulseIcon },
  { href: "/admin/fill-health", label: "Fill Health", icon: HeartbeatIcon },
  { href: "/admin/fill-reports", label: "Fill Reports", icon: BugBeetleIcon },
] as const;

const ROW =
  "rounded-control text-label focus-visible:ring-brand-ring flex items-center gap-2.5 px-3 py-2 whitespace-nowrap transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none";
const QUIET = "text-ink-muted hover:bg-rail-hover hover:text-ink";
/** The current page: a white pill with the brand's ink on the pale violet rail. */
const CURRENT = "bg-panel text-brand-ink ring-rail-border shadow-xs ring-1";

/**
 * The admin shell's sidebar (KAN-879): the logo, a link per admin page and
 * Back to WorkIt. From lg up it is a column that collapses to a rail of
 * icons; below lg it is a bar above the page, with no collapse. A collapsed
 * row keeps its name for screen readers and as a tooltip.
 *
 * It wears WorkIt's rail tokens (`rail`, `rail-hover`, `rail-border`), the
 * pale violet the company shell's sidebar has, so violet stays the colour
 * of what is on or acts. It was dark ink first, then a violet gradient
 * under two lights: a design review found the gradient was decoration, and
 * one label on it fell to 3.9:1.
 *
 * It clips with `overflow-clip`, never `overflow-hidden`: a hidden box
 * still scrolls, and on the collapsed rail the screen-reader-only words
 * scrolled every icon out of view.
 */
// ponytail: the collapse is not kept across a reload; localStorage if the team asks.
export function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  /** Hides a row's words on the collapsed rail only; below lg the bar always shows them. */
  const words = collapsed ? "lg:sr-only" : undefined;

  return (
    <aside
      className={cn(
        "bg-rail border-rail-border flex shrink-0 items-center gap-4 overflow-x-auto border-b px-3 py-2",
        "lg:flex-col lg:items-stretch lg:gap-6 lg:overflow-clip lg:border-r lg:border-b-0 lg:py-5",
        collapsed ? "lg:w-16" : "lg:w-60",
      )}
    >
      <div
        className={cn(
          "flex items-center gap-2",
          collapsed ? "lg:flex-col lg:gap-4" : "lg:justify-between lg:pl-3",
        )}
      >
        <span className="flex items-center gap-2">
          <Logo size="mark" />
          <span className={cn("text-subtitle text-ink max-lg:sr-only", words)}>Admin</span>
        </span>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          className={cn(ROW, QUIET, "px-2 max-lg:hidden")}
        >
          <SidebarSimpleIcon size={18} aria-hidden />
        </button>
      </div>
      <nav aria-label="Admin" className="flex gap-1 lg:flex-col">
        {PAGES.map(({ href, label, icon: Icon }) => {
          const current = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={current ? "page" : undefined}
              title={collapsed ? label : undefined}
              className={cn(ROW, current ? CURRENT : QUIET, collapsed && "lg:justify-center")}
            >
              <Icon size={18} weight={current ? "fill" : "regular"} aria-hidden />
              <span className={words}>{label}</span>
            </Link>
          );
        })}
      </nav>
      <Link
        href="/go-home"
        title={collapsed ? "Back to WorkIt" : undefined}
        className={cn(ROW, QUIET, "ml-auto lg:mt-auto lg:ml-0", collapsed && "lg:justify-center")}
      >
        <ArrowLeftIcon size={18} aria-hidden />
        <span className={words}>Back to WorkIt</span>
      </Link>
    </aside>
  );
}
