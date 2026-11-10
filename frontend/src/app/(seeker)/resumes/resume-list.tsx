import type { ReactNode } from "react";

import { ResumeScroll } from "@/components/resume-list";

/**
 * The Resumes page's list (KAN-362): every resume's card (an upload's
 * `ResumeRow`, a built resume's ./built-resume-row.tsx) under its group's
 * heading (`ResumeGroup`, KAN-404), in one card that scrolls inside itself
 * (`ResumeScroll`, components/resume-list.tsx, shared with the resume
 * picker since KAN-406) down to the foot of the page (`fill`, KAN-434), so
 * the search and the buttons above it stay in view however many resumes a
 * student keeps. The cards hold all a resume
 * needs: its name, one line saying what it is ("Uploaded Oct 21", "Last
 * edited Oct 21 · For …"), and its star, Rename, Download and Delete. A
 * table with Type and Last Edited columns, then with the icons in one menu,
 * came first in KAN-362: the columns said what each card's line already
 * says, and the menu hid the actions a student uses.
 *
 * Since 2026-11-10 the cards sit on the page's ground, as the Tracker's do,
 * each a white card with its dates in columns (`ResumeCard`), and the list
 * is no card of its own: grey strips in a white card read skinny and
 * cramped to the user. The scroll's own inset (`ResumeScroll`'s px-3, the
 * room a card's shadow needs) is taken back with -mx-3, so the cards line
 * up with the search and the buttons above.
 */
export function ResumeList({ children }: { children: ReactNode }) {
  return (
    <section aria-label="Your Resumes" className="-mx-3 mt-1">
      <ResumeScroll fill>{children}</ResumeScroll>
    </section>
  );
}
