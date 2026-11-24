import type { ReactNode } from "react";

import { TabLinks } from "@/components/ui/tabs";
import { PAGE_SEARCH } from "@/components/ui/search-field";

export type ResumesView = "resumes" | "cover-letters" | "experiences";

/**
 * The header of Documents' two tabs and of Experiences: on Documents
 * (/resumes and /cover-letters, KAN-766), a row of tabs, Resumes then Cover
 * Letters, over the view's search on the left and its actions on the
 * right; on Experiences, the search and its action alone. On a phone the
 * search takes a line of its own. The section's title is in the top bar
 * (../bar-title.tsx). The tabs are plain links between two routes, not a
 * shallow move, since each reads its own data on the server.
 *
 * Resumes and Experiences were two pages until KAN-249, then two views of
 * one page behind a switcher (Resumes & Experiences) until KAN-766, which
 * gave Experiences its own sidebar row again: it is the source every
 * resume, match and written answer reads, not a kind of document, and the
 * switcher, which is for two looks of the same content, sat where a tab
 * should. Documents' tabs are tabs (`ui/tabs.tsx`) for the same reason.
 */
export function ResumesHeader({
  view,
  search,
  action,
}: {
  view: ResumesView;
  search?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4">
      {view !== "experiences" && (
        <TabLinks
          ruled
          label="Documents"
          value={view}
          options={[
            { value: "resumes", label: "Resumes", href: "/resumes" },
            { value: "cover-letters", label: "Cover Letters", href: "/cover-letters" },
          ]}
        />
      )}
      {(search || action) && (
        <div className="flex flex-wrap items-center gap-3">
          {search}
          {action && (
            <div className="ml-auto flex flex-wrap items-center justify-end gap-3">{action}</div>
          )}
        </div>
      )}
    </header>
  );
}

/** The width of a search in this header: every page's (`PAGE_SEARCH`). */
export const RESUMES_SEARCH = PAGE_SEARCH;
