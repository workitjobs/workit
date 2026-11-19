"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";

import { INFO_ROOT, infoSection } from "./auto-apply/info/sections";
import { BAR_TITLE } from "./bar";

/** Each section's title, the first match of a page's path. A nested path sits
 *  before its parent. A new seeker section joins this list. */
const TITLES = [
  ["/jobs", "Jobs"],
  ["/auto-apply/answers", "Written Answers"],
  ["/auto-apply/info", "Application Info"],
  ["/auto-apply", "Auto Apply"],
  ["/auto-apply-desktop", "Auto Apply Desktop"],
  ["/applications", "Tracker"],
  ["/resumes", "Documents"],
  ["/cover-letters", "Documents"],
  ["/experiences", "Experiences"],
  ["/calendar", "Calendar"],
  ["/profile", "Profile"],
  ["/inbox", "Inbox"],
  ["/help", "Help"],
] as const;

/** Settings, a modal over the page it opened from (./settings/settings-modal.tsx). */
const isSettings = (path: string) => path === "/settings" || path.startsWith("/settings/");

/**
 * The page's title in the top bar (2026-11-02), with no line under it: each
 * page had its own heading and description, about 60px on every screen.
 *
 * Read from the address, not sent up by the page, so the title is there before
 * the page streams in and stays put while a job's page swaps beside the rail.
 *
 * It is the page's h1 on a section's own page. A page under it (a job, a
 * resume, an application) has its own h1, and here the section's name is a
 * plain line. `home` is Home's greeting, which the layout reads on the server.
 *
 * A modal never changes it. With Settings open the bar keeps the title of the
 * page behind, its h1 included, and the dialog names itself: the bar said
 * "Settings" over Jobs, and the page's h1 was gone. A hard load of a Settings
 * address opens over Home (./settings/layout.tsx), so Home's title is the one
 * kept there.
 */
export function BarTitle({ home }: { home: ReactNode }) {
  const address = usePathname();
  const [behind, setBehind] = useState(isSettings(address) ? "/home" : address);
  if (!isSettings(address) && address !== behind) setBehind(address);
  const pathname = isSettings(address) ? behind : address;

  if (pathname === "/home") return home;
  if (pathname === "/search") {
    return (
      <Suspense fallback={<h1 className={BAR_TITLE}>Search Jobs</h1>}>
        <SearchTitle />
      </Suspense>
    );
  }

  const found = TITLES.find(([path]) => pathname === path || pathname.startsWith(`${path}/`));
  if (!found) return null;
  const [path, title] = found;
  const Tag = pathname === path || isInfoPart(pathname) ? "h1" : "p";
  return <Tag className={BAR_TITLE}>{title}</Tag>;
}

/**
 * Application Info's parts are pages of one page (./auto-apply/info), each
 * under its menu with its card's title as an h2, so the bar's "Application
 * Info" is the h1 on each, as on a section's own page. It was a plain line
 * there, and the parts had no h1 (KAN-822). An unknown part is a 404, which
 * is its own h1.
 */
const isInfoPart = (pathname: string) =>
  pathname.startsWith(`${INFO_ROOT}/`) && infoSection(pathname.slice(INFO_ROOT.length + 1)) != null;

/** Apart from the rest because useSearchParams suspends on a prerendered route
 *  (./search/query-field.tsx). */
function SearchTitle() {
  const query = useSearchParams().get("q")?.trim();
  const title = query ? `Results for “${query}”` : "Search Jobs";
  return (
    <h1 title={title} className={BAR_TITLE}>
      {title}
    </h1>
  );
}
