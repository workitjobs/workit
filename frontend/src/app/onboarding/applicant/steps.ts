import type { FeedFilters } from "@/app/(seeker)/jobs/filter-query";

/**
 * Onboarding's pages, in order (./onboarding-form). Two tracks.
 *
 * SETUP is what every new student answers: one question, or two that belong
 * together, on each page, after Figma's sign-up (2026-11-16). The old wizard
 * put seven questions on its first page and seven more on Profile, and the
 * student scrolled a long form under one heading. Setup ends on Contact,
 * whose Finish saves the answers and opens the Jobs page: once the
 * preferences and the resume are in, the student can browse, tailor and
 * apply, so nothing more stands between them and the jobs.
 *
 * The resume comes before Authorization and Contact (KAN-372) because
 * saving it fills the profile's location and links from its header
 * (KAN-436), so Contact opens filled in.
 *
 * EXTENSION is the extension's own track: its install, the optional Add
 * Claude page (KAN-507) and a practice batch (KAN-378). Setup no longer
 * leads into it. Only `EXTENSION_STEP_PATH` opens it, from
 * `/extension-setup`'s "I Already Have One" (KAN-495), and Auto Apply's
 * setup row asks for the extension where it is needed. It was setup's last
 * three pages until 2026-11-16, so a student reached the Jobs page only
 * after a Chrome install and a practice run.
 *
 * Availability (KAN-369), Citizenship and Visa Status and Security
 * Clearance left onboarding on 2026-11-16: few forms need them before the
 * first application, and Application Info asks them with the rest of the
 * Application answers.
 */
/*
 * ONE QUESTION A PAGE, AND NO PAGE SCROLLS (2026-11-17): Start Date,
 * Sponsorship and Links were each the second half of a page (Job Type,
 * Authorization, Contact) until those pages ran past a laptop's window; each
 * is its own page now. Start Date shows only once Internship is picked
 * (`skippedPage`), since only internships name a season.
 *
 * Location was the second half of Where until 2026-11-17: under the
 * workplace tiles its button read as an extra. Where asks how (On-Site,
 * Hybrid, Remote), Location where, and Location is skipped when Remote is
 * the only workplace picked, since a remote job has no office to reach.
 */
export const SETUP_PAGES = [
  "Role",
  "JobType",
  "StartDate",
  "Level",
  "Where",
  "Location",
  "Pay",
  "Resume",
  "Authorization",
  "Sponsorship",
  "Contact",
  "Links",
] as const;

export const EXTENSION_PAGES = ["Extension", "Claude", "Practice"] as const;

export const WIZARD_PAGES = [...SETUP_PAGES, ...EXTENSION_PAGES] as const;

export type Page = (typeof WIZARD_PAGES)[number];

/** The page's index by name. */
export const pageOf = (name: Page) => WIZARD_PAGES.indexOf(name);

/**
 * NOT SURE YET (2026-11-17): every setup question can be left open, the
 * required ones too. A student who does not yet know what role, job type or
 * place they want is the student onboarding is for, and a required page
 * with no way past it told them to guess. Not Sure Yet clears the page's
 * answer, which on the Jobs page means every option (no role filter is
 * every role), and goes on. The resume page is a task, not a preference,
 * so its way past is Decide Later; Contact's fields are all optional and
 * Find Jobs already goes on without them.
 */
export const UNSURE_PAGES = [
  "Role",
  "JobType",
  "StartDate",
  "Level",
  "Where",
  "Location",
  "Pay",
  "Authorization",
  "Sponsorship",
] as const satisfies readonly Page[];

export type UnsurePage = (typeof UNSURE_PAGES)[number];

export const isUnsurePage = (page: Page): page is UnsurePage =>
  (UNSURE_PAGES as readonly Page[]).includes(page);

/** What Not Sure Yet clears on a preference page, so the Jobs page shows
 *  every option there; null for a page whose answers are not filters
 *  (Authorization's are the answer bank's, cleared by the form). */
export function unsureClears(page: UnsurePage): Partial<FeedFilters> | null {
  switch (page) {
    case "Role":
      return { roles: [], customRoles: [] };
    case "JobType":
      // A start date belongs to the job type picked with it.
      return { jobTypes: [], startTerms: [] };
    case "StartDate":
      return { startTerms: [] };
    case "Level":
      return { levels: [] };
    case "Where":
      return { workStyles: [] };
    case "Location":
      return { places: [] };
    case "Pay":
      return { minPay: null, maxPay: null };
    case "Authorization":
    case "Sponsorship":
      return null;
  }
}

/** The answers that decide which pages show. */
type Shown = Pick<FeedFilters, "jobTypes" | "workStyles">;

/** Whether the wizard passes over a page for these answers: Start Date
 *  asks for a season, which only an internship names, and Location for a
 *  place, which a remote-only student has no office in. */
export function skippedPage(page: Page, answers: Shown): boolean {
  if (page === "StartDate") return !answers.jobTypes.includes("internship");
  if (page === "Location")
    return answers.workStyles.length > 0 && answers.workStyles.every((w) => w === "remote");
  return false;
}

/** The page after (or, with `by` -1, before) `from`, past the pages these
 *  answers skip; it never leaves the wizard. */
export function nextPage(from: number, by: 1 | -1, answers: Shown): number {
  let at = from + by;
  while (at > 0 && at < WIZARD_PAGES.length - 1 && skippedPage(WIZARD_PAGES[at], answers)) at += by;
  return Math.min(Math.max(at, 0), WIZARD_PAGES.length - 1);
}

/** The first page of the track `page` is on: Back stops there. */
export function trackStart(page: number): number {
  return page < SETUP_PAGES.length ? 0 : SETUP_PAGES.length;
}

/** How far through its track `page` is, 0 to 1, counting the page itself
 *  as done: the progress bar at the column's foot. */
export function progress(page: number): number {
  const setup = page < SETUP_PAGES.length;
  const done = page - trackStart(page) + 1;
  return done / (setup ? SETUP_PAGES.length : EXTENSION_PAGES.length);
}

/** Each page's address, `?step=<slug>`: the wizard writes it as the
 *  student moves (./onboarding-form), so a reload, a shared link or a
 *  bookmark opens that page. Until 2026-11-16 the page lived only in the
 *  wizard's state, and no page past the first could be opened directly. */
export const PAGE_SLUGS: Record<Page, string> = {
  Role: "role",
  JobType: "job-type",
  StartDate: "start-date",
  Level: "level",
  Where: "where",
  Location: "location",
  Pay: "pay",
  Resume: "resume",
  Authorization: "authorization",
  Sponsorship: "sponsorship",
  Contact: "contact",
  Links: "links",
  Extension: "extension",
  Claude: "claude",
  Practice: "practice",
};

/** The page a slug names, or -1. */
export function pageOfSlug(slug: string): number {
  return WIZARD_PAGES.findIndex((page) => PAGE_SLUGS[page] === slug);
}

/** The extension track's link: `/extension-setup`'s "I Already Have One"
 *  (KAN-495), and sign-in's `next` (lib/sign-in-next.ts). */
export const EXTENSION_STEP_PATH = "/onboarding/applicant?step=extension";

/**
 * The page ./page opens on, from its `?step=`, a page's slug (PAGE_SLUGS).
 * A setup page opens for anyone: Find Jobs sends a student back to the first
 * required answer still missing, so opening Contact first saves nothing
 * half done. An extension track page opens only for a seeker with saved
 * answers or who finished onboarding (`finished`): its pages save nothing
 * and lead to the Jobs page, so a new student who opened one would skip
 * setup. Loading the extension must never send a finished seeker back to
 * fill in everything again (2026-11-01). Anything else opens setup's first
 * page.
 */
export function startStep(
  param: string | string[] | undefined,
  saved: boolean,
  finished = false,
): number {
  const page = typeof param === "string" ? pageOfSlug(param) : -1;
  if (page < 0) return 0;
  if (page >= SETUP_PAGES.length && !(saved || finished)) return 0;
  return page;
}
