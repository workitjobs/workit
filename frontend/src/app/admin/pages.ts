import {
  BugBeetleIcon,
  FileMagnifyingGlassIcon,
  HeartbeatIcon,
  PulseIcon,
} from "@phosphor-icons/react/ssr";

/**
 * The admin pages and each page's sections (KAN-879), in one place: the
 * sidebar draws a link per page and, under it, a link per section, and each
 * page gives its sections these ids, so a section link always has its
 * target. A section's `label` is also its card's title on the page.
 *
 * This file is not a client file on purpose: the pages (server) and the
 * sidebar (client) both read it, and a server file that reads a value from
 * a "use client" file gets Next's client stub in its place
 * (`frontend/CLAUDE.md`, Admin pages).
 */

export type AdminSection = {
  /** The section's element id: the address fragment (`#board-reads`) that scrolls to it. */
  id: string;
  label: string;
};

export const SCRAPE_SECTIONS = {
  status: { id: "status", label: "Status" },
  perDay: { id: "reads-per-day", label: "Board Reads per Day" },
  attention: { id: "needs-attention", label: "Needs Attention" },
  systems: { id: "hiring-systems", label: "Boards by Hiring System" },
  reads: { id: "board-reads", label: "Board Reads" },
} as const satisfies Record<string, AdminSection>;

export const FILL_SECTIONS = {
  metrics: { id: "metrics", label: "Metrics" },
  fills: { id: "fills", label: "Fills" },
} as const satisfies Record<string, AdminSection>;

export const READING_SECTIONS = {
  status: { id: "status", label: "Status" },
  perDay: { id: "readings-per-day", label: "Readings per Day" },
  reasons: { id: "no-ai-reasons", label: "Why AI Did Not Read" },
  accuracy: { id: "accuracy", label: "Accuracy" },
  models: { id: "models", label: "Models" },
  readings: { id: "recent-readings", label: "Recent Readings" },
} as const satisfies Record<string, AdminSection>;

export const REPORT_SECTIONS = {
  groups: { id: "groups", label: "Groups" },
  reports: { id: "reports", label: "Reports" },
} as const satisfies Record<string, AdminSection>;

/** The admin pages, in the sidebar's order. A new admin page joins this list, with its sections. */
export const ADMIN_PAGES = [
  {
    href: "/admin/scrape-health",
    label: "Scrape Health",
    icon: PulseIcon,
    sections: Object.values(SCRAPE_SECTIONS),
  },
  {
    href: "/admin/fill-health",
    label: "Fill Health",
    icon: HeartbeatIcon,
    sections: Object.values(FILL_SECTIONS),
  },
  {
    href: "/admin/resume-reading",
    label: "Resume Reading",
    icon: FileMagnifyingGlassIcon,
    sections: Object.values(READING_SECTIONS),
  },
  {
    href: "/admin/fill-reports",
    label: "Fill Reports",
    icon: BugBeetleIcon,
    sections: Object.values(REPORT_SECTIONS),
  },
] as const satisfies readonly {
  href: string;
  label: string;
  icon: typeof PulseIcon;
  sections: readonly AdminSection[];
}[];

/** Where a section stops when its link scrolls to it: 24px under the top, the page's own top padding. */
export const SECTION_TARGET = "scroll-mt-6";
/**
 * The same for a page's first section, which sits under the page's title
 * row: 192px, more than that row's height at any width the links show at,
 * so the link shows the page from its top, the title and its controls
 * included. At 24px the title row was scrolled out of view.
 */
export const FIRST_SECTION_TARGET = "scroll-mt-48";
