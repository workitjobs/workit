"use client";

import { ArrowLeftIcon, CaretDownIcon, SidebarSimpleIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type MouseEvent, useState } from "react";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

import { ADMIN_PAGES } from "./pages";

const FOCUS = "focus-visible:ring-brand-ring focus-visible:ring-2 focus-visible:outline-none";
const ROW = cn(
  "rounded-control text-label flex items-center gap-2.5 px-3 py-2 whitespace-nowrap transition-colors duration-150",
  FOCUS,
);
const QUIET = "text-ink-muted hover:bg-rail-hover hover:text-ink";
/** The current page: a white pill with the brand's ink on the pale violet rail. */
const CURRENT = "bg-panel text-brand-ink ring-rail-border shadow-xs ring-1";
/** A section's link under its page: a step smaller and quieter than a page's row. */
const SECTION = cn(
  "rounded-control text-note text-ink-meta hover:bg-rail-hover hover:text-ink block px-2 py-1.5 transition-colors duration-150",
  FOCUS,
);

/**
 * Scrolls to a section of the page the admin is on, on every press of its
 * link. Next scrolls to a fragment only when the fragment changes
 * (`url.hash !== oldUrl.hash` in its navigation), so a second press on the
 * same section, after the admin scrolled away, did nothing: the address
 * already said `#status`. When the address already has the fragment, the
 * press is stopped here, since a link to the address the page is at would
 * only read the page again. The scroll glides or jumps as the page's own
 * box says (`admin/layout.tsx`).
 */
function goTo(id: string, event: MouseEvent<HTMLAnchorElement>) {
  const section = document.getElementById(id);
  if (!section) return;
  section.scrollIntoView();
  if (window.location.hash === `#${id}`) event.preventDefault();
}

/**
 * The admin shell's sidebar (KAN-879): the logo, a link per admin page and
 * Back to WorkIt. From lg up it is a column that collapses to a rail of
 * icons; below lg it is a bar above the page, with no collapse. A collapsed
 * row keeps its name for screen readers and as a tooltip.
 *
 * UNDER EACH PAGE, A LINK PER SECTION of that page (`./pages.ts`), which
 * goes to the section: on the page itself the link is the fragment alone
 * (`#board-reads`), so the address keeps its period and position, and from
 * another page it is that page's address with the fragment. They show from
 * lg up on the open sidebar only: the rail has icons alone, and the bar
 * below lg is one row.
 *
 * THE SECTION LINKS ARE CLOSED UNTIL THEIR ARROW OPENS THEM. Each page with
 * sections has a small arrow at the end of its row, a button of its own
 * that shows or hides that page's links and goes nowhere. The links were
 * always open at first, seven lines under three pages, and the user asked
 * for the arrow so they show only when wanted (2026-11-22).
 *
 * It wears WorkIt's rail tokens (`rail`, `rail-hover`, `rail-border`), the
 * pale violet the company shell's sidebar has, so violet stays the colour
 * of what is on or acts. It was dark ink first, then a violet gradient
 * under two lights: a design review found the gradient was decoration, and
 * one label on it fell to 3.9:1.
 *
 * It clips with `overflow-clip`, never `overflow-hidden`: a hidden box
 * still scrolls, and on the collapsed rail the screen-reader-only words
 * scrolled every icon out of view. Only the links' own box scrolls, down
 * the page and never across it.
 */
// ponytail: the collapse and the open section lists are not kept across a reload; localStorage if the team asks.
// ponytail: no section is marked as the one in view; a scroll observer if the team asks.
export function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  /** The pages whose section links show, by address. None at first: the arrow opens them. */
  const [open, setOpen] = useState<readonly string[]>([]);
  const toggle = (href: string) =>
    setOpen(open.includes(href) ? open.filter((other) => other !== href) : [...open, href]);
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
      {/* From lg up the links scroll inside the sidebar when the window is short, so the
          section links never push Back to WorkIt out of reach. The 4px of padding, taken
          back by the margin, keeps a row's focus ring inside the scrolling box. */}
      <nav aria-label="Admin" className="lg:-m-1 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:p-1">
        <ul className="flex gap-1 lg:flex-col">
          {ADMIN_PAGES.map(({ href, label, icon: Icon, sections }) => {
            const current = pathname === href || pathname.startsWith(`${href}/`);
            const shown = open.includes(href);
            const listId = `admin-sections-${href.slice(href.lastIndexOf("/") + 1)}`;
            return (
              <li key={href}>
                <div className="relative">
                  <Link
                    href={href}
                    aria-current={current ? "page" : undefined}
                    title={collapsed ? label : undefined}
                    className={cn(
                      ROW,
                      current ? CURRENT : QUIET,
                      collapsed ? "lg:justify-center" : "lg:pr-9",
                    )}
                  >
                    <Icon size={18} weight={current ? "fill" : "regular"} aria-hidden />
                    <span className={words}>{label}</span>
                  </Link>
                  {/* Beside the page's link, never inside it: a press on the arrow opens the
                    list and goes nowhere. It sits in the room the link's padding leaves. */}
                  <button
                    type="button"
                    onClick={() => toggle(href)}
                    aria-expanded={shown}
                    aria-controls={listId}
                    aria-label={`${shown ? "Hide" : "Show"} ${label} Sections`}
                    className={cn(
                      "text-ink-meta hover:bg-rail-hover hover:text-ink rounded-control absolute top-1/2 right-1 flex size-7 -translate-y-1/2 items-center justify-center transition-colors duration-150 max-lg:hidden",
                      FOCUS,
                      collapsed && "lg:hidden",
                    )}
                  >
                    <CaretDownIcon
                      size={14}
                      weight="bold"
                      aria-hidden
                      className={cn(
                        "transition-transform duration-150 motion-reduce:transition-none",
                        shown && "rotate-180",
                      )}
                    />
                  </button>
                </div>
                <ul
                  id={listId}
                  aria-label={`${label} Sections`}
                  className={cn(
                    "border-rail-border mt-1 ml-5 flex-col border-l pl-2 max-lg:hidden",
                    shown ? "flex" : "hidden",
                    collapsed && "lg:hidden",
                  )}
                >
                  {sections.map((section) => (
                    <li key={section.id}>
                      <Link
                        // The fragment alone on the page itself, so the address keeps its query.
                        href={pathname === href ? `#${section.id}` : `${href}#${section.id}`}
                        onClick={pathname === href ? (event) => goTo(section.id, event) : undefined}
                        className={SECTION}
                      >
                        {section.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
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
