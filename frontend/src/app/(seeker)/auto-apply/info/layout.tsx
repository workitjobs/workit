import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../../gutter";
import { InfoNav } from "./info-nav";

/**
 * /auto-apply/info — Application Info (KAN-550): everything the extension
 * and the student's Claude fill into a form that is not on a resume. It all
 * sat on My Profile until KAN-550, which made that page a long form the
 * student scrolled past to find their own name and links: what an employer
 * sees stays there, and what only the autofiller reads moved here, under
 * the feature that uses it.
 *
 * ONE PART A PAGE (2026-11-11): its menu (./info-nav.tsx) beside the part
 * open (./[section]/page.tsx), each part at /auto-apply/info/<part>
 * (./sections.ts), so the menu stays in view and the student reads one
 * part at a time. It was six cards down one page under a list of anchor
 * links until then. On a phone the menu is a row above the part. The
 * layout reads nothing: each part reads its own, under ./loading.tsx.
 * A <div>, since SidebarInset is already the <main>.
 */
export default function ApplicationInfoLayout({ children }: { children: ReactNode }) {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <div className="grid gap-6 sm:grid-cols-[13rem_minmax(0,1fr)] sm:gap-8">
        <InfoNav />
        <div className="flex min-w-0 flex-col gap-5">
          <p className="text-body text-ink-meta">
            What WorkIt and your Claude fill into your applications, beyond your resume. Only you
            can see these.
          </p>
          {children}
        </div>
      </div>
    </div>
  );
}
