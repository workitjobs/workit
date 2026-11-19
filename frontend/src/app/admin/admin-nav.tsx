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
  "rounded-control text-label flex items-center gap-2.5 px-3 py-2 whitespace-nowrap focus-visible:outline-on-inverse focus-visible:outline-2";
const QUIET = "text-on-inverse/65 hover:text-on-inverse hover:bg-white/5";

/**
 * The admin shell's sidebar (KAN-879): the logo, a link per admin page and
 * Back to WorkIt. From lg up it is a column that collapses to a rail of
 * icons; below lg it is a bar above the page, with no collapse. A collapsed
 * row keeps its name for screen readers and as a tooltip.
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
        "bg-inverse flex shrink-0 items-center gap-4 overflow-x-auto px-3 py-2",
        "lg:flex-col lg:items-stretch lg:gap-6 lg:overflow-visible lg:py-5",
        collapsed ? "lg:w-16" : "lg:w-60",
      )}
    >
      <div
        className={cn(
          "text-on-inverse flex items-center gap-2",
          collapsed ? "lg:flex-col lg:gap-4" : "lg:justify-between lg:pl-3",
        )}
      >
        <span className="flex items-center gap-2">
          <Logo size="mark" className="text-on-inverse" />
          <span className={cn("text-body font-semibold max-lg:sr-only", words)}>Admin</span>
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
              className={cn(
                ROW,
                current ? "bg-brand text-on-brand" : QUIET,
                collapsed && "lg:justify-center",
              )}
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
