"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import { TabLinks } from "@/components/ui/tabs";

import { INFO_ROOT, partHref } from "./info/sections";

const ANSWERS = "/auto-apply/answers";
const DESKTOP = "/auto-apply/desktop";

const under = (pathname: string, path: string) =>
  pathname === path || pathname.startsWith(`${path}/`);

/**
 * Auto Apply's tabs (./layout.tsx), Documents' own (`ui/tabs.tsx`, ruled):
 * Queue, Application Info and Desktop App, the section's three pages. They
 * replaced the setup row, three cards over the queue that linked the same
 * pages (2026-11-10 to 2026-11-23), and the rail's Auto Apply Desktop row
 * (KAN-835): cards that looked alike read as three required steps, and a
 * download page is not a place a student works in.
 *
 * NO WRITTEN ANSWERS TAB. It was the third tab for a few hours on
 * 2026-11-23, with a count, and the user took it out: the queue is where a
 * student manages each job, a row's status says its questions wait, and
 * the notice over the queue leads to Written Answers (./up-next.tsx). That
 * page is a page under the queue, with its own Back, so the tabs are not
 * drawn on it.
 *
 * ON A PHONE THE ROW MAY SCROLL SIDEWAYS. The scroll is on a wrapper and
 * the tabs keep their own width (`min-w-max`), so the open tab's underline
 * still sits on the rule; with the scroll on the tabs' own row, the rule's
 * line was clipped away. The wrapper's padding leaves the focus ring room.
 * The open tab is scrolled into the row sideways only: `scrollIntoView`
 * moved the page too, on a return to a page scrolled down.
 */
export function AutoApplyTabs() {
  const pathname = usePathname();
  const hidden = under(pathname, ANSWERS);
  const value = under(pathname, INFO_ROOT)
    ? "info"
    : under(pathname, DESKTOP)
      ? "desktop"
      : "queue";

  const row = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = row.current;
    const tab = box?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!box || !tab) return;
    const frame = box.getBoundingClientRect();
    const at = tab.getBoundingClientRect();
    if (at.left < frame.left) box.scrollLeft -= frame.left - at.left + 16;
    else if (at.right > frame.right) box.scrollLeft += at.right - frame.right + 16;
  }, [value]);

  if (hidden) return null;
  return (
    // mb-4: Documents' gap between its tabs and its toolbar.
    <div ref={row} className="-mx-1 -mt-1 mb-4 [scrollbar-width:none] overflow-x-auto px-1 pt-1">
      <TabLinks
        ruled
        label="Auto Apply"
        value={value}
        className="min-w-max"
        options={[
          { value: "queue", label: "Queue", href: "/auto-apply" },
          { value: "info", label: "Application Info", href: partHref("work-authorization") },
          { value: "desktop", label: "Desktop App", href: DESKTOP },
        ]}
      />
    </div>
  );
}
