import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { logoStrip, problems } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob } from "./feature-data";
import { delay, Panel } from "./scene-parts";

/**
 * The three screens of the problems section (problems.tsx, problem-tabs.tsx,
 * KAN-923), each in the wide flat frame. Mock UI of the search as it is,
 * before WorkIt, so nothing here is violet. Each plays once as it shows
 * (the `.journey-*` and `.scan-*` classes), finished without script and
 * with reduced motion. All are `aria-hidden`: the problem cards beside them
 * say what they show.
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

/** Where a window stands: centred, its top inset, its foot cut by the
 *  frame. Each window is at least 34rem tall, taller than the frame at
 *  every width, so its foot never shows. */
const STAGE = "absolute inset-x-0 top-0 px-3 pt-6 sm:px-10 sm:pt-10";

/** A phrase the screen marks as it reads: a keyword it looks for, or a
 *  line that reads as generic. `at` is seconds into the document's turn,
 *  just after the scan line passes it. */
type Marked = { mark: string; tone: "match" | "generic"; at: number };
type Line = readonly (string | Marked)[];

/** The student's one resume, sent to every posting: three of the posting's
 *  six keywords, and a line any resume could hold. */
const RESUME: { head: string; sub: string; sections: { title: string; lines: Line[] }[] } = {
  head: "Alex Morgan",
  sub: "Northview University · Computer Science",
  sections: [
    {
      title: "Experience",
      lines: [
        ["Built a budget app with ", { mark: "React", tone: "match", at: 1.0 }],
        [{ mark: "Hard-working team player", tone: "generic", at: 1.1 }],
        [
          "Analyzed survey data with ",
          { mark: "Python", tone: "match", at: 1.18 },
          " and ",
          { mark: "SQL", tone: "match", at: 1.2 },
        ],
        ["Made a website for a student club"],
      ],
    },
    {
      title: "Skills",
      lines: [
        ["Excel, Microsoft Office, ", { mark: "detail-oriented", tone: "generic", at: 1.45 }],
      ],
    },
  ],
};

/** The cover letter that goes out with it: the same words any letter has. */
const LETTER: Line[] = [
  ["Dear Hiring Manager,"],
  [
    { mark: "I am writing to express my interest", tone: "generic", at: 0.8 },
    " in the position at your company.",
  ],
  [
    "I am a ",
    { mark: "passionate team player", tone: "generic", at: 1.0 },
    " who loves technology.",
  ],
  [{ mark: "I would be a great fit", tone: "generic", at: 1.16 }, " for your team."],
  [{ mark: "Thank you for your time and consideration.", tone: "generic", at: 1.28 }],
  ["Sincerely,"],
  ["Alex Morgan"],
];

/** What the screen reads, one at a time: the resume, its cover letter, the
 *  resume again for the next posting, where it rests. */
const DOCS = [
  { paper: "resume", verdict: "3 of 6 keywords" },
  { paper: "letter", verdict: "Reads as generic" },
  { paper: "resume", verdict: "3 of 6 keywords" },
] as const;

/**
 * Screened out: one application at a time comes into a hiring system's
 * screen, a scan line reads it top to bottom, marking the keywords it
 * looks for and the lines that read as generic, and it is flagged Not
 * moved forward and swiped away; the next comes in. The last, the resume,
 * rests marked with its verdict. From lg up the applications waiting sit
 * on its left and the ones it turned away pile up on its right, so it
 * reads as a machine that keeps going; each document comes off the one and
 * lands on the other (`.scan-*` in landing.css reads their spacing). Below
 * lg a document leaves off the frame's edge. Inspired by the archived statement's
 * marked phrases, without its art: no bin, stamp or crumpled page (the
 * team found those AI-made). It never shows a document passing: the site
 * never promises that. Timing: `.scan-*` in landing.css, one 3.6s turn per
 * document.
 */
export function ScreenScene() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 flex items-center justify-center gap-10 px-4 pt-4 pb-16"
    >
      <Pile label="Waiting" count={211} />
      <div className="flex h-full max-h-[22rem] w-full max-w-[17rem] flex-col items-center">
        <span className="text-ink-muted inline-flex shrink-0 items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold shadow-[var(--mk-shadow-float)]">
          <span className="size-1.5 rounded-full bg-slate-400" />
          Screening · {problems.screen.role}
        </span>
        <div className="relative mt-3 w-full flex-1">
          <Corners />
          {DOCS.map((doc, i) => (
            <div
              key={i}
              className={cn(
                "scan-anim absolute inset-2.5",
                i === DOCS.length - 1 ? "scan-doc-last" : "scan-doc",
              )}
              style={{ "--i": i } as CSSProperties}
            >
              <div className="h-full overflow-hidden rounded-md bg-white p-4 shadow-[var(--mk-shadow-float)]">
                {doc.paper === "resume" ? <ResumePaper /> : <LetterPaper />}
              </div>
              <div className="scan-anim scan-verdict absolute inset-x-0 -bottom-3 flex justify-center gap-1.5">
                <span className="text-ink-muted rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap shadow-[var(--mk-shadow-float)]">
                  {doc.verdict}
                </span>
                <span className="bg-danger-tint text-danger rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap shadow-[var(--mk-shadow-float)]">
                  Not moved forward
                </span>
              </div>
            </div>
          ))}
          <div className="pointer-events-none absolute inset-2.5 overflow-hidden rounded-md">
            <div className="scan-anim scan-line absolute inset-0">
              <span className="absolute inset-x-0 top-0 h-8 -translate-y-full bg-linear-to-t from-slate-500/15 to-transparent" />
              <span className="absolute inset-x-0 top-0 h-0.5 bg-slate-500/60" />
            </div>
          </div>
        </div>
      </div>
      <Pile label="Not moved forward" count={186} out />
    </div>
  );
}

/** Each paper in a pile: turned a little, offset, so the pile reads as
 *  several. */
const STACKED = [
  { x: -6, y: 6, r: -4 },
  { x: 5, y: 2, r: 3 },
  { x: 0, y: 0, r: -1 },
];

/**
 * A pile of applications beside the screen, from lg up: the ones waiting on
 * its left, the ones it turned away on its right (`out`, greyed, its count
 * in the danger colour). Blank pages with lines for text: what matters is
 * how many.
 */
function Pile({ label, count, out = false }: { label: string; count: number; out?: boolean }) {
  return (
    <div className="flex h-full max-h-[18rem] w-[11rem] shrink-0 flex-col items-center justify-center max-lg:hidden">
      <div className="relative min-h-0 w-full flex-1">
        {STACKED.map((paper) => (
          <span
            key={paper.r}
            className={cn(
              "absolute inset-0 grid content-start gap-1.5 rounded-md p-3.5 shadow-[var(--mk-shadow-float)]",
              out ? "bg-slate-50" : "bg-white",
            )}
            style={{ translate: `${paper.x}px ${paper.y}px`, rotate: `${paper.r}deg` }}
          >
            <span className="mx-auto mb-1 block h-2 w-1/2 rounded-full bg-slate-900/15" />
            {[100, 90, 95, 70, 85, 60].map((width, i) => (
              <span
                key={i}
                className="block h-1.5 rounded-full bg-slate-900/[0.08]"
                style={{ width: `${width}%` }}
              />
            ))}
          </span>
        ))}
      </div>
      <p className="mt-4 shrink-0 text-center text-[11px] leading-tight">
        <span
          className={cn(
            "block text-[15px] font-semibold tabular-nums",
            out ? "text-danger" : "text-ink",
          )}
        >
          {count}
        </span>
        <span className="text-ink-meta">{label}</span>
      </p>
    </div>
  );
}

/** The screen's frame: four corner marks round the document it reads. */
function Corners() {
  const corner = "absolute size-4 border-slate-900/30";
  return (
    <>
      <span className={cn(corner, "top-0 left-0 rounded-tl-md border-t-2 border-l-2")} />
      <span className={cn(corner, "top-0 right-0 rounded-tr-md border-t-2 border-r-2")} />
      <span className={cn(corner, "bottom-0 left-0 rounded-bl-md border-b-2 border-l-2")} />
      <span className={cn(corner, "right-0 bottom-0 rounded-br-md border-r-2 border-b-2")} />
    </>
  );
}

/** A line of a document, its marked phrases tinted as the scan passes. */
function Words({ line }: { line: Line }) {
  return line.map((part, i) =>
    typeof part === "string" ? (
      <span key={i}>{part}</span>
    ) : (
      <span
        key={i}
        className={cn(
          "scan-anim scan-mark rounded-[3px] px-0.5",
          part.tone === "match"
            ? "[--mark:var(--color-positive-tint)]"
            : "[--mark:var(--color-danger-tint)]",
        )}
        style={{ "--t": `${part.at}s` } as CSSProperties}
      >
        {part.mark}
      </span>
    ),
  );
}

function ResumePaper() {
  return (
    <div className="text-ink text-[10.5px] leading-[1.55]">
      <p className="text-center text-[13px] font-semibold">{RESUME.head}</p>
      <p className="text-ink-meta text-center text-[10px]">{RESUME.sub}</p>
      {RESUME.sections.map((section) => (
        <div key={section.title} className="mt-3">
          <p className="text-ink-meta border-b border-slate-900/10 pb-0.5 text-[9px] font-semibold tracking-[0.08em] uppercase">
            {section.title}
          </p>
          <ul className="mt-1.5 grid gap-1">
            {section.lines.map((line, i) => (
              <li key={i} className="flex gap-1.5">
                <span className="text-ink-meta">•</span>
                <span>
                  <Words line={line} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function LetterPaper() {
  return (
    <div className="text-ink grid gap-2 text-[10.5px] leading-[1.55]">
      {LETTER.map((line, i) => (
        <p key={i}>
          <Words line={line} />
        </p>
      ))}
    </div>
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
