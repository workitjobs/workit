"use client";

import { BugBeetleIcon, HeartbeatIcon, PulseIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

/** The admin pages, in the sidebar's order. A new admin page joins this list. */
const PAGES = [
  { href: "/admin/scrape-health", label: "Scrape Health", icon: PulseIcon },
  { href: "/admin/fill-health", label: "Fill Health", icon: HeartbeatIcon },
  { href: "/admin/fill-reports", label: "Fill Reports", icon: BugBeetleIcon },
] as const;

/** The admin shell's links: a column in the sidebar, a row above the page below lg. */
export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Admin" className="flex gap-1 lg:flex-col">
      {PAGES.map(({ href, label, icon: Icon }) => {
        const current = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "rounded-control text-label flex items-center gap-2.5 px-3 py-2 whitespace-nowrap",
              "focus-visible:outline-on-inverse focus-visible:outline-2",
              current
                ? "bg-brand text-on-brand"
                : "text-on-inverse/65 hover:text-on-inverse hover:bg-white/5",
            )}
          >
            <Icon size={18} weight={current ? "fill" : "regular"} aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
