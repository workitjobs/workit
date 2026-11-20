import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { logoStrip, problems } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob } from "./feature-data";
import { delay, Panel } from "./scene-parts";

/**
 * The three screens of the problems section (problems.tsx, problem-tabs.tsx,
 * KAN-923): each a real-looking window at about true size, standing in the
 * wide frame and cut by its foot, after the taste rules' "chapter" (one
 * screen shown big, never a small picture centred on a coloured panel).
 * Mock UI of the search as it is, before WorkIt, so nothing here is violet.
 * Each plays once as it shows (the `.journey-*` and `.ats-*` classes),
 * finished without script and with reduced motion. All are `aria-hidden`:
 * the problems' words beside them say what they show.
 */

/** Three window dots, as a desktop window's title bar has. */
function Dots() {
  return (
    <span className="flex shrink-0 gap-1">
      {[0, 1, 2].map((dot) => (
        <span key={dot} className="size-2 rounded-full bg-slate-900/15" />
      ))}
    </span>
  );
}

/** Where a screen's window stands: centred, its top inset, its foot cut by
 *  the frame. Each window is at least 34rem tall, taller than the frame at
 *  every width, so its foot never shows. */
const STAGE = "absolute inset-x-0 top-0 px-3 pt-6 sm:px-10 sm:pt-10";

/** The applicant screen's row and cut-off line heights, which the
 *  arrival's slide reads (`.ats-shift`, `.ats-you` in landing.css). */
const ATS = { "--ats-row": "2.5rem", "--ats-cut": "1.5rem" } as CSSProperties;

/** The other applicants, sorted as the screen sorts them: by how many of
 *  the posting's keywords each resume has. */
const ABOVE = [
  { initials: "JP", found: 6 },
  { initials: "MR", found: 6 },
  { initials: "AK", found: 5 },
];
const BELOW = [
  { initials: "DT", found: 2 },
  { initials: "SL", found: 2 },
  { initials: "RV", found: 1 },
  { initials: "KO", found: 1 },
];

/** Applicant, keywords, status. On a phone the keywords are the count
 *  alone and an applicant is their initials (the file name went: cut to
 *  "resume.…", it read as a glitch). */
const COLUMNS =
  "gap-x-2 grid-cols-[minmax(0,1fr)_3.75rem_7.5rem] sm:grid-cols-[minmax(0,1fr)_9rem_9rem]";

/**
 * Screened out: a hiring system's applicant list as a recruiter's team sees
 * it, screening on the posting's keywords. The student's resume, the one
 * they send everywhere, arrives at the top as New, is scored (3 of the 6
 * keywords) and slides to its place under the screening cut-off: Not moved
 * forward. It never shows the resume passing: the site never promises that.
 */
export function ScreenScene() {
  const { role, keywords } = problems.screen;
  const yours = keywords.filter((keyword) => keyword.found).length;
  return (
    <div aria-hidden="true" className={STAGE} style={ATS}>
      <Panel className="mx-auto min-h-[34rem] w-full max-w-[44rem] overflow-hidden rounded-b-none">
        <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-4 py-2.5">
          <Dots />
          <span className="text-ink-muted ml-1.5 text-[11px] font-semibold">Applicants</span>
          <span className="text-ink-meta truncate text-[11px]">{role}</span>
          <span className="text-ink-meta ml-auto shrink-0 text-[11px] tabular-nums">
            214 applicants
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-900/[0.06] px-4 py-2.5">
          <span className="text-ink-meta mr-1 text-[11px]">Screen on</span>
          {keywords.map((keyword) => (
            <span
              key={keyword.word}
              className="text-ink-muted rounded-full bg-slate-900/[0.05] px-2 py-0.5 text-[11px]"
            >
              {keyword.word}
            </span>
          ))}
        </div>
        <div
          className={cn(
            "text-ink-meta grid px-4 pt-2.5 pb-1.5 text-[10px] font-semibold tracking-[0.06em] uppercase",
            COLUMNS,
          )}
        >
          <span>Applicant</span>
          <span>Keywords</span>
          <span>Status</span>
        </div>
        <div className="relative">
          {ABOVE.map((applicant) => (
            <Applicant key={applicant.initials} {...applicant} total={keywords.length} up />
          ))}
          <div className="ats-shift flex h-6 items-center gap-2 px-4">
            <span className="flex-1 border-t border-dashed border-slate-900/25" />
            <span className="text-ink-meta text-[10px] font-semibold tracking-[0.06em] uppercase">
              Screening cut-off
            </span>
            <span className="flex-1 border-t border-dashed border-slate-900/25" />
          </div>
          <div
            className={cn(
              "ats-you relative z-10 mx-1.5 grid h-10 items-center rounded-lg bg-white px-2.5 shadow-[var(--mk-shadow-float)] ring-1 ring-slate-900/10",
              COLUMNS,
            )}
          >
            <span className="flex min-w-0 items-center gap-2">
              <span className="bg-ink grid h-5 shrink-0 place-items-center rounded-full px-1.5 text-[10px] font-semibold text-white">
                You
              </span>
              <span className="text-ink truncate text-[12px] font-medium max-sm:hidden">
                resume.pdf
              </span>
            </span>
            <Score found={yours} total={keywords.length} tone="bg-danger" at={0.8} />
            <span className="grid">
              <span className="ats-gone text-ink-muted col-start-1 row-start-1 w-fit rounded-full bg-slate-900/[0.06] px-2 py-0.5 text-[11px] font-semibold">
                New
              </span>
              <span
                className="journey-in bg-danger-tint text-danger col-start-1 row-start-1 w-fit rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap"
                style={delay(2.2)}
              >
                Not moved forward
              </span>
            </span>
          </div>
          {BELOW.map((applicant) => (
            <Applicant key={applicant.initials} {...applicant} total={keywords.length} />
          ))}
        </div>
      </Panel>
    </div>
  );
}

/** Another applicant's row: initials, their keyword score, their status. */
function Applicant({
  initials,
  found,
  total,
  up = false,
}: {
  initials: string;
  found: number;
  total: number;
  up?: boolean;
}) {
  return (
    <div
      className={cn(
        "grid h-10 items-center border-t border-slate-900/[0.05] px-4",
        COLUMNS,
        up && "ats-shift",
      )}
    >
      <span className="flex min-w-0 items-center gap-2">
        <span className="text-ink-meta grid size-6 shrink-0 place-items-center rounded-full bg-slate-900/[0.06] text-[10px] font-semibold">
          {initials}
        </span>
        <span
          className={cn("truncate text-[12px] max-sm:hidden", up ? "text-ink" : "text-ink-meta")}
        >
          resume.pdf
        </span>
      </span>
      <Score found={found} total={total} tone={up ? "bg-positive" : "bg-slate-400"} />
      <span
        className={cn(
          "w-fit rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
          up ? "bg-positive-tint text-positive-ink" : "text-ink-meta bg-slate-900/[0.05]",
        )}
      >
        {up ? "Moved forward" : "Not moved forward"}
      </span>
    </div>
  );
}

/** A resume's keyword score: a short bar and "n of 6". With `at`, it fills
 *  and its count shows that many seconds into the screen's play. */
function Score({
  found,
  total,
  tone,
  at,
}: {
  found: number;
  total: number;
  tone: string;
  at?: number;
}) {
  return (
    <span className="flex items-center gap-2">
      <span className="hidden h-1.5 w-14 overflow-hidden rounded-full bg-slate-900/[0.07] sm:block">
        <span
          className={cn("block h-full rounded-full", tone, at !== undefined && "journey-grow")}
          style={{ width: `${(found / total) * 100}%`, ...(at !== undefined && delay(at)) }}
        />
      </span>
      <span
        className={cn(
          "text-ink-meta text-[11px] tabular-nums",
          at !== undefined && "journey-in text-ink",
        )}
        style={at !== undefined ? delay(at) : undefined}
      >
        {found} of {total}
      </span>
    </span>
  );
}

/** The companies whose forms the student fills, one after another. */
const FORMS = [
  { company: "Stripe", domain: "stripe.com" },
  { company: "Notion", domain: "notion.so" },
  { company: "Figma", domain: "figma.com" },
];

/** The same questions on every company's form, answered the same way. */
const FIELDS = [
  { label: "First name", value: "Alex" },
  { label: "Last name", value: "Morgan" },
  { label: "School", value: "Northview University" },
  { label: "Graduation date", value: "May 2027" },
  { label: "Work experience", value: null },
  { label: "Why this company?", value: null },
];

/**
 * The same form, again: three companies' application forms side by side,
 * the same six questions on each, typed in one form after another with the
 * same answers. Below lg they run off the frame's right edge: more forms
 * waiting.
 */
export function FormsScene() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-x-0 top-0 flex justify-start gap-4 px-5 pt-6 sm:px-10 sm:pt-10 lg:justify-center"
    >
      {FORMS.map((form, f) => (
        <Panel
          key={form.company}
          // Taller than the frame, so the frame's foot cuts every form.
          className="journey-in min-h-[34rem] w-[15.5rem] shrink-0 rounded-b-none p-4"
          style={delay(0.1 + f * 0.1)}
        >
          <div className="flex items-center gap-2">
            <FaviconLogo domain={form.domain} className="size-6 rounded-md" />
            <span className="text-ink text-[12px] font-semibold">Apply to {form.company}</span>
          </div>
          <div className="mt-3 grid gap-2.5">
            {FIELDS.map((field, i) => (
              <div key={field.label}>
                <p className="text-ink-meta text-[10px] font-medium">{field.label}</p>
                <div
                  className={cn(
                    "bg-well mt-1 flex items-center rounded-md px-2",
                    field.value ? "h-6" : "h-10 items-start py-1.5",
                  )}
                >
                  <span className="journey-in w-full" style={delay(0.5 + f * 0.9 + i * 0.12)}>
                    {field.value ? (
                      <span className="text-ink text-[11px]">{field.value}</span>
                    ) : (
                      <span className="grid gap-1">
                        <span className="block h-1.5 w-full rounded-full bg-slate-900/15" />
                        <span className="block h-1.5 w-3/4 rounded-full bg-slate-900/15" />
                      </span>
                    )}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}

/** One company's open roles, as its own job board lists them: every team
 *  and level in one list, and the one that fits the student in among them. */
const ROLES = [
  { title: "Staff Software Engineer, Payments", place: "San Francisco, Seattle" },
  { title: "Senior Data Scientist, Risk", place: "New York" },
  { title: "Engineering Manager, Billing", place: "San Francisco" },
  { title: "Senior Product Designer", place: "Remote in US" },
  { title: followedJob.title, place: "San Francisco, New York" },
  { title: "Account Executive, Enterprise", place: "Chicago" },
  { title: "Solutions Architect", place: "Dublin" },
  { title: "Senior Backend Engineer, Ledger", place: "Seattle" },
];

/**
 * Good jobs, scattered: a browser crowded with company job board tabs, one
 * tab after another opening, and the open one, followed Stripe's, listing
 * every role at every level with the internship that fits somewhere in the
 * middle, marked by nothing.
 */
export function BoardsScene() {
  const tabs = logoStrip.employers.slice(0, 9);
  return (
    <div aria-hidden="true" className={STAGE}>
      <Panel className="mx-auto min-h-[34rem] w-full max-w-[46rem] overflow-hidden rounded-b-none">
        <div className="flex items-end gap-1 bg-slate-900/[0.04] px-2 pt-2">
          {tabs.map((employer, i) => (
            <span
              key={employer.domain}
              className={cn(
                "journey-in flex min-w-0 flex-1 items-center gap-1.5 rounded-t-md px-2 py-1.5",
                i === 0 && "bg-white",
                i > 2 && "max-sm:hidden",
                i > 4 && "max-lg:hidden",
              )}
              style={delay(0.1 + i * 0.12)}
            >
              <FaviconLogo domain={employer.domain} className="size-4 rounded-[4px] shadow-none" />
              <span className="text-ink-muted truncate text-[11px]">{employer.name} Careers</span>
            </span>
          ))}
          <span
            className="journey-in text-ink-meta shrink-0 px-2 pb-1.5 text-[11px] tabular-nums"
            style={delay(1.2)}
          >
            +31
          </span>
        </div>
        <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 py-2">
          <Dots />
          <span className="bg-well text-ink-meta ml-1 flex-1 truncate rounded-full px-3 py-1 text-[11px]">
            {followedJob.domain}/jobs/search
          </span>
        </div>
        <div className="px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="text-ink text-[15px] font-semibold">Open roles</span>
            <span className="text-ink-meta ml-auto rounded-md px-2 py-0.5 text-[11px] ring-1 ring-slate-900/10">
              All teams
            </span>
            <span className="text-ink-meta rounded-md px-2 py-0.5 text-[11px] ring-1 ring-slate-900/10">
              All locations
            </span>
          </div>
          <ul className="mt-3">
            {ROLES.map((role, i) => (
              <li
                key={role.title}
                className="journey-in flex items-baseline gap-3 border-t border-slate-900/[0.05] py-2"
                style={delay(1 + i * 0.06)}
              >
                <span className="text-ink truncate text-[12px] font-medium">{role.title}</span>
                <span className="text-ink-meta ml-auto shrink-0 text-[11px] max-sm:hidden">
                  {role.place}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Panel>
    </div>
  );
}
