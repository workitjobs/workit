"use client";

import {
  BriefcaseIcon,
  CalendarDotsIcon,
  FileTextIcon,
  ListChecksIcon,
  HouseIcon,
  StackIcon,
  TrayIcon,
  UserCircleIcon,
} from "@phosphor-icons/react/ssr";
import { LightningRoundedIcon } from "@/components/custom-icons";
import type { ReactNode } from "react";

import { AppSidebar, type SidebarNavGroup } from "@/components/app-sidebar";

import { INBOX_LIVE } from "./inbox/live";

/**
 * The seeker shell's left panel, the rail (see RAIL in
 * @/components/app-sidebar): the hunt itself, the sections a job seeker
 * moves between all through a search, Home first as the home, with no
 * caption over them. These used to be tabs in the top bar.
 *
 * Nothing about the app rather than the work lives here. Settings, Help and
 * Sign Out were a second group, General, under this one; they moved to the
 * menu the bar's photo opens (SeekerAccount in ./account-status.tsx), where
 * people look for them, so the panel holds only the search and each of
 * those has one home. There is no Sign In anywhere in the shell: it only
 * renders for someone signed in, and the layout sends anyone else to
 * /login.
 *
 * There is no Search row. /search is where the bar's own field lands a query
 * (and, on a phone, the bar's magnifier), and a row beside that field would
 * be a second, contradictory way to reach it.
 *
 * Auto Apply sits between Jobs and Applications, in the order the work goes:
 * find the jobs, apply to them, track what was sent. It carries the queue's
 * count (./queue-badge.tsx, 2026-11-09), the queue's one status outside its
 * page; the Inbox's count was taken out as out of place, but a queue's is a
 * count of work waiting on the seeker's own pipeline.
 *
 * Applications' glyph is ListChecks, what the page is for (tracking what was
 * sent), not how it is laid out. It was SquareKanban, the board's shape, and
 * went stale when the list replaced the board (KAN-256, KAN-317). Not
 * ClipboardList: a framed page with lines, it read as FileText, the next
 * row down.
 *
 * Inbox and Calendar sit after Documents (KAN-426): they hold
 * what comes back once applications are out, replies and dated events, so
 * the tools for applying come first and the follow-up after them.
 * Calendar's glyph is CalendarDots, not CalendarBlank: the plain calendar is
 * the Interviewing stage's glyph (../stage-colors.ts), and a nav row wearing
 * it would read as a stage.
 *
 * Profile is a row rather than something behind the account in the bar:
 * a profile is somewhere a job seeker goes back to all through a hunt, not
 * somewhere they visit once, and a click of depth is the wrong price for
 * that. It was "My Profile" until 2026-11-05; in the seeker's own shell no
 * employer's profile is ever named, so "My" told nothing apart.
 *
 * Experiences and Documents sit right after the Applications Tracker,
 * beside the work they feed: every application goes out with a resume, and
 * every resume is made from the experiences. Experiences (/experiences,
 * where resume facts are kept, KAN-206) comes first, as the source; its
 * glyph is Stack, entries kept one on another. Documents is one row for
 * its two tabs, Resumes (/resumes, with the resume editor under it) and
 * Cover Letters (/cover-letters), lit on either (`also`); its glyph is
 * FileText, the one on Generate Resume. Resumes and Experiences were two
 * rows (Experience Bank, My Resumes) until KAN-249, one row behind a
 * switcher (Resumes & Experiences) until KAN-766, and two rows again since,
 * with cover letters joining the resumes.
 *
 * One set of names (2026-11-05): Tracker, Experiences, Documents and
 * Profile on the rail and on the phone's sheet alike. They were the rail's
 * short names, beside "Applications Tracker", "Resumes & Experiences" and
 * "My Profile" on the sheet, and the user found two names for one section
 * confusing. The bar's title, page titles, Back links and breadcrumbs use
 * the same names.
 */
/** Whether the Calendar row shows (2026-11-09). Off while the Calendar does
 *  not work: a greyed-out row on every page was a promise the app could not
 *  keep. Its page stays at /calendar, unlinked from the rail. Set it to true
 *  to bring the row back, live. */
const CALENDAR_LIVE = false;

const GROUPS: SidebarNavGroup[] = [
  {
    // No caption: with one group there is nothing to tell it apart from.
    items: [
      { href: "/home", label: "Home", Icon: HouseIcon },
      { href: "/jobs", label: "Jobs", Icon: BriefcaseIcon },
      { href: "/auto-apply", label: "Auto Apply", Icon: LightningRoundedIcon },
      { href: "/applications", label: "Tracker", Icon: ListChecksIcon },
      // KAN-766: Experiences is the source every resume, match and answer
      // reads, so it has its own row, before the documents made from it.
      // Documents holds the resumes and cover letters, as tabs. The two
      // shared one row (Resumes & Experiences) from KAN-249 until then.
      { href: "/experiences", label: "Experiences", Icon: StackIcon },
      { href: "/resumes", also: ["/cover-letters"], label: "Documents", Icon: FileTextIcon },
      // KAN-413: replies to applications, after the tools that send them.
      // No count badge: one was built and taken out as out of place.
      // Archived with the Inbox until WorkIt has a source of emails
      // (KAN-428, ./inbox/live.ts).
      ...(INBOX_LIVE ? [{ href: "/inbox", label: "Inbox", Icon: TrayIcon }] : []),
      // Back since KAN-413: interviews, assessments and offers are stored.
      // Greyed out (2026-11-02) while it does not work, then taken off the
      // rail (2026-11-09, CALENDAR_LIVE) until it does.
      ...(CALENDAR_LIVE ? [{ href: "/calendar", label: "Calendar", Icon: CalendarDotsIcon }] : []),
      { href: "/profile", label: "Profile", Icon: UserCircleIcon },
    ],
  },
];

/** `card` is the profile strength card, rendered on the server by the layout
 *  (it reads the API) and passed through, since this panel is a client
 *  component. */
export function SeekerSidebar({
  card,
  queueBadge,
}: {
  card?: ReactNode;
  /** The Auto Apply row's count (./queue-badge.tsx), streamed in by the
   *  layout, which reads the queue. */
  queueBadge?: ReactNode;
}) {
  const groups = GROUPS.map((group) => ({
    ...group,
    items: group.items.map((item) =>
      "href" in item && item.href === "/auto-apply" ? { ...item, badge: queueBadge } : item,
    ),
  }));
  return (
    <AppSidebar
      groups={groups}
      footerCard={card}
      label="Job Search Sections"
      variant="rail"
      home="/home"
    />
  );
}
