import type { ReactNode } from "react";

import { ResumeScroll } from "@/components/resume-list";
import {
  RESUME_ACTIONS_COL,
  RESUME_DATE_COL,
  RESUME_TH,
  RESUME_TYPE_COL,
} from "@/components/resume-row";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/shadcn/table";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

/**
 * The Resumes page's resumes (KAN-362), in the layout the student picked
 * (KAN-766): every resume's row or card (an upload's `ResumeRow`, a built
 * resume's ./built-resume-row.tsx), in the sort's order, with no group
 * headings since 2026-11-10.
 *
 * **The list is a table after the Tracker's** (`applications/list.tsx`,
 * 2026-11-10): one white card, 12px grey headings (Name, Type, Date
 * Modified, and the actions' column with no heading), rules between the
 * rows and no box around each. The page scrolls, as the Tracker's does.
 * The headings name each column once; as wide cards on the page's ground,
 * each resume labeled its own date "Modified" or "Created", which the user
 * found repetitive. A table came once before, in KAN-362, and the user
 * found its columns useless beside cards that each said what they were;
 * the user asked for it back once the grid needed a list that read as the
 * Tracker's. Unlike the Tracker's, its columns do not move, resize or hide:
 * a resume has four facts, not twelve. Below `@2xl` of the table the Type
 * column folds to nothing and the date drops its time.
 *
 * **The grid** is the resumes' first pages, in a card-free scroll that runs
 * down to the foot of the page (`ResumeScroll`'s `fill`, KAN-434), so the
 * search and the buttons above stay in view. The scroll's own inset (its
 * px-3, the room a card's shadow needs) is taken back with -mx-3, so the
 * cards line up with the search and the buttons above.
 */
export function ResumeList({
  grid = false,
  children,
}: {
  /** The grid of first pages (KAN-766), not the table. */
  grid?: boolean;
  children: ReactNode;
}) {
  if (grid) {
    return (
      <section aria-label="Your Resumes" className="@container -mx-3 mt-1">
        <ResumeScroll fill grid>
          {children}
        </ResumeScroll>
      </section>
    );
  }
  return (
    <Card padding="none" className="@container mt-4 overflow-hidden">
      <Table aria-label="Your Resumes" className="table-fixed">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={RESUME_TH}>Name</TableHead>
            <TableHead className={cn(RESUME_TH, RESUME_TYPE_COL)}>
              <span className="hidden @2xl:inline">Type</span>
            </TableHead>
            <TableHead className={cn(RESUME_TH, RESUME_DATE_COL)}>Date Modified</TableHead>
            <TableHead className={RESUME_ACTIONS_COL}>
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>{children}</TableBody>
      </Table>
    </Card>
  );
}
