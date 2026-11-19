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
  "rounded-control text-label flex items-center gap-2.5 px-3 py-2.5 whitespace-nowrap transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";
/** A row that is not the current page: white at 85%, which holds 4.5:1 on the violet's lightest part. */
const QUIET = "text-white/85 hover:bg-white/15 hover:text-white";
/** The current page: a white pill with the brand's ink, the one solid shape on the violet. */
const CURRENT = "text-brand-ink bg-white shadow-md";

/**
 * The admin shell's sidebar (KAN-879): the logo, a link per admin page and
 * Back to WorkIt. From lg up it is a column that collapses to a rail of
 * icons; below lg it is a bar above the page, with no collapse. A collapsed
 * row keeps its name for screen readers and as a tooltip.
 *
 * It is WorkIt's violet, running from the brand colour down to its darkest
 * step, under two soft lights. It was the dark ink first, which the user
 * found was not WorkIt's colour. It clips with `overflow-clip`, never
 * `overflow-hidden`: a hidden box still scrolls, and on the collapsed rail
 * the screen-reader-only words scrolled every icon out of view.
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
        "from-brand to-brand-active relative isolate flex shrink-0 items-center gap-4 overflow-x-auto bg-linear-to-b px-3 py-2",
        "lg:flex-col lg:items-stretch lg:gap-6 lg:overflow-clip lg:px-3.5 lg:py-5",
        collapsed ? "lg:w-16" : "lg:w-60",
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute -top-16 -left-16 -z-10 size-56 rounded-full bg-white/20 blur-3xl max-lg:hidden"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -right-20 bottom-10 -z-10 size-56 rounded-full bg-white/10 blur-3xl max-lg:hidden"
      />
      <div
        className={cn(
          "flex items-center gap-2 text-white",
          collapsed ? "lg:flex-col lg:gap-4" : "lg:justify-between lg:pl-3",
        )}
      >
        <span className="flex items-center gap-2">
          <span className="rounded-control bg-white p-1.5 shadow-sm">
            <Logo size="mark" />
          </span>
          <span className={cn("text-base font-semibold tracking-tight max-lg:sr-only", words)}>
            WorkIt Admin
          </span>
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
        <p className={cn("text-caption px-3 pb-1 text-white/70 uppercase max-lg:hidden", words)}>
          Monitoring
        </p>
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
        className={cn(
          ROW,
          QUIET,
          "ml-auto lg:mt-auto lg:ml-0 lg:rounded-t-none lg:border-t lg:border-white/20 lg:pt-4",
          collapsed && "lg:justify-center",
        )}
      >
        <ArrowLeftIcon size={18} aria-hidden />
        <span className={words}>Back to WorkIt</span>
      </Link>
    </aside>
  );
}
