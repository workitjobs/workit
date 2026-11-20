import type { Icon as PhosphorIcon } from "@phosphor-icons/react";
import {
  ArrowCounterClockwiseIcon,
  BriefcaseIcon,
  CheckIcon,
  CodeIcon,
  FileArrowDownIcon,
  GraduationCapIcon,
  PlusIcon,
  ScissorsIcon,
  WarningIcon,
  WrenchIcon,
} from "@phosphor-icons/react/ssr";

import { SparkleIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

import { FaviconLogo } from "../../favicon-logo";
import { candidate, followedJob, matchingFeature } from "../../feature-data";
import { Label, Vignette } from "./parts";

/** The Resume Builder page's deep dives, with the tour's student and the
 *  Stripe posting every stop follows (feature-data.ts). */

const BANK: { section: string; icon: PhosphorIcon; title: string; detail: string }[] = [
  {
    section: "Education",
    icon: GraduationCapIcon,
    title: "B.S. Computer Science",
    detail: "Northview University",
  },
  {
    section: "Experience",
    icon: BriefcaseIcon,
    title: "Teaching Assistant",
    detail: "Data Structures",
  },
  {
    section: "Experience",
    icon: BriefcaseIcon,
    title: "IT Support Intern",
    detail: "Campus Help Desk",
  },
  { section: "Projects", icon: CodeIcon, title: "Budget Tracker", detail: "React · Node.js" },
];

/** The experience bank, filled from an uploaded resume. */
export function BankVisual() {
  return (
    <Vignette className="px-6">
      <div className="surface-card rounded-2xl p-4">
        <div className="flex items-center justify-between">
          <p className="text-ink text-[13px] font-semibold">Experience Bank</p>
          <span className="bg-positive-tint text-positive-ink inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
            <CheckIcon className="size-3" weight="bold" />
            Read from Alex_Morgan_Resume.pdf
          </span>
        </div>
        <div className="mt-2.5 grid gap-1">
          {BANK.map(({ section, icon: Icon, title, detail }) => (
            <div
              key={title}
              className="flex items-center gap-2.5 rounded-xl bg-white px-2.5 py-1 ring-1 ring-slate-900/5"
            >
              <span className="bg-advanced-tint text-advanced grid size-7 shrink-0 place-items-center rounded-lg">
                <Icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-ink truncate text-[11px] font-semibold">{title}</p>
                <p className="text-ink-meta text-[10px]">{detail}</p>
              </div>
              <span className="text-ink-muted text-[10px] font-medium">{section}</span>
            </div>
          ))}
        </div>
        <div className="mt-2.5 flex items-center gap-1.5">
          <WrenchIcon className="text-ink-meta size-3.5" />
          {matchingFeature.profile.skills.map((skill) => (
            <span
              key={skill}
              className="text-ink rounded-full bg-slate-50 px-2 py-0.5 text-[10px] font-medium ring-1 ring-slate-900/5"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>
    </Vignette>
  );
}

/** Jake's Resume is set in Latin Modern; the closest faces a browser has
 *  (resume-visual.tsx). */
const JAKES_FACE = '"Latin Modern Roman", "CMU Serif", "Computer Modern", Georgia, serif';

/** A bullet's line on the page, as a bar of its length. */
function Line({ width }: { width: string }) {
  return <span className="block h-[5px] rounded-full bg-slate-300/70" style={{ width }} />;
}

function PageSection({
  name,
  entries,
  typed,
}: {
  name: string;
  entries: [string, string][];
  /** The first entry's first bullet, being typed on the page. */
  typed?: string;
}) {
  return (
    <div className="mt-2.5">
      <p className="text-ink border-b border-slate-400 pb-0.5 text-[9px] font-bold tracking-wide uppercase">
        {name}
      </p>
      {entries.map(([title, place], i) => (
        <div key={title} className="mt-1.5">
          <p className="text-ink flex justify-between gap-2 text-[9px] font-bold">
            {title}
            <span className="font-normal italic">{place}</span>
          </p>
          <div className="mt-1 grid gap-1 pl-2">
            {i === 0 && typed ? <TypedLine text={typed} /> : <Line width="92%" />}
            <Line width="78%" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** A bullet open in the editor: the field over the line, in the page's own
 *  face, with the editor's 1.5px ring and a caret (frontend/docs/screens.md,
 *  Resume editor, "Click a line and type"). */
function TypedLine({ text }: { text: string }) {
  return (
    <span className="ring-advanced text-ink relative -mx-1 block rounded-[3px] bg-white px-1 py-0.5 text-[8px] leading-tight ring-[1.5px]">
      • {text}
      <span
        aria-hidden="true"
        className="caret-blink bg-ink ml-px inline-block h-[9px] w-px align-[-1px]"
      />
    </span>
  );
}

/** A resume generated from the bank, in Jake's Resume, edited on the page
 *  (a bullet being typed), and the Download menu's three formats. */
export function BuildVisual() {
  return (
    <Vignette className="items-center">
      <div
        className="w-[230px] bg-white px-5 py-4 shadow-[0_24px_48px_-24px_rgb(15_23_42/0.3)] ring-1 ring-slate-900/8"
        style={{ fontFamily: JAKES_FACE }}
      >
        <p className="text-ink text-center text-[15px] font-bold">{candidate.name}</p>
        <p className="text-ink-meta text-center text-[8px]">
          alex@example.com · linkedin.com/in/alexmorgan
        </p>
        {/* The typed line sits in Education, above the Download menu: in
            Experience the menu covered it. */}
        <PageSection
          name="Education"
          typed="Coursework: Data Structures, Algorithms"
          entries={[["Northview University", "May 2027"]]}
        />
        <PageSection
          name="Experience"
          entries={[
            ["Teaching Assistant", "Data Structures"],
            ["IT Support Intern", "Campus Help Desk"],
          ]}
        />
      </div>
      <div className="surface-card absolute right-6 bottom-8 w-28 rounded-xl p-1.5">
        <p className="text-ink flex items-center gap-1 px-1.5 pt-0.5 pb-1 text-[11px] font-semibold">
          <FileArrowDownIcon className="size-3.5" />
          Download
        </p>
        {["PDF", "Word", "LaTeX"].map((format, i) => (
          <p
            key={format}
            className={cn(
              "text-ink rounded-md px-1.5 py-1 text-[11px]",
              i === 0 && "bg-advanced-tint",
            )}
          >
            {format}
          </p>
        ))}
      </div>
    </Vignette>
  );
}

/** A resume over one page in the editor: the Projects section runs past the
 *  page break, and the editor's own Over One Page notice offers Fit to One
 *  Page (`FitToast` in resumes/[resumeId]/fit-notice.tsx, its words and
 *  button). Projects is the section Fit gives way first of those shown
 *  (docs/cut_to_one_page.md). */
export function FitVisual() {
  return (
    <Vignette className="items-start pl-5">
      <div
        className="w-[192px] bg-white px-4 py-3.5 shadow-[0_24px_48px_-24px_rgb(15_23_42/0.3)] ring-1 ring-slate-900/8"
        style={{ fontFamily: JAKES_FACE }}
      >
        <p className="text-ink text-center text-[14px] font-bold">{candidate.name}</p>
        <PageSection name="Education" entries={[["Northview University", "May 2027"]]} />
        <PageSection
          name="Experience"
          entries={[
            ["Teaching Assistant", "Data Structures"],
            // Short, so title and place share a line on the narrower page.
            ["IT Support Intern", "Help Desk"],
          ]}
        />
        {/* The page break, as the editor's pages meet: what is under it
            runs onto page 2. */}
        <div className="relative -mx-4 mt-3 border-t border-dashed border-slate-400">
          <span className="text-ink-muted absolute -top-[7px] left-2 bg-white px-1 font-sans text-[8px] font-semibold">
            Page 2
          </span>
        </div>
        <PageSection name="Projects" entries={[["Budget Tracker", "React · Node.js"]]} />
      </div>
      <div className="surface-card absolute right-3 bottom-8 flex w-[164px] items-start gap-2 rounded-xl p-3">
        <span className="bg-warning-tint text-warning grid size-6 shrink-0 place-items-center rounded-full">
          <WarningIcon className="size-3.5" />
        </span>
        <div className="min-w-0">
          <p className="text-ink text-[11px] font-semibold">Over One Page</p>
          <p className="text-ink-meta mt-0.5 text-[9.5px] leading-snug">
            About 4 lines run onto page 2.
          </p>
          <span className="bg-ink mt-2 inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-semibold whitespace-nowrap text-white">
            <ScissorsIcon className="size-3" />
            Fit to One Page
          </span>
        </div>
      </div>
    </Vignette>
  );
}

/** Tailor's keyword step: what the resume shows, the missing keywords the
 *  student picks, and a reworded bullet in the editor with its Undo. */
export function TailorVisual() {
  const ring = 2 * Math.PI * 26;
  const missing = [
    {
      label: "Required",
      keywords: [
        ["TypeScript", true],
        ["REST APIs", true],
      ],
    },
    { label: "Preferred", keywords: [["GraphQL", false]] },
  ] as const;
  return (
    <Vignette className="gap-3 px-4">
      <div className="surface-card flex gap-4 rounded-2xl p-4">
        <div className="flex w-[84px] shrink-0 flex-col items-center gap-1">
          <svg viewBox="0 0 64 64" className="size-16 -rotate-90">
            <circle
              cx="32"
              cy="32"
              r="26"
              fill="none"
              strokeWidth="7"
              className="stroke-slate-200"
            />
            <circle
              cx="32"
              cy="32"
              r="26"
              fill="none"
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={`${ring * 0.6} ${ring}`}
              className="stroke-advanced"
            />
          </svg>
          <p className="text-ink text-[11px] font-semibold">6 of 10</p>
          <p className="text-ink-meta text-[9px]">keywords on it</p>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-ink text-[12px] font-semibold">Add the Keywords You Have Used</p>
          {missing.map((group) => (
            <div key={group.label} className="mt-2">
              <Label>{group.label}</Label>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {group.keywords.map(([keyword, picked]) => (
                  <span
                    key={keyword}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset",
                      picked
                        ? "bg-advanced-tint text-advanced ring-advanced/40"
                        : "text-ink bg-white ring-slate-900/10",
                    )}
                  >
                    {picked ? (
                      <CheckIcon className="size-3" weight="bold" />
                    ) : (
                      <PlusIcon className="size-3" />
                    )}
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          ))}
          <span className="bg-ink mt-3 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-semibold text-white">
            <SparkleIcon className="size-3.5" />
            Tailor Resume
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3 rounded-xl bg-white px-3 py-2 ring-1 ring-slate-900/5">
        <p className="text-ink min-w-0 flex-1 text-[11px] leading-snug">
          <span className="bg-advanced-tint rounded-[3px] px-0.5">
            Built a budget tracker in TypeScript and React on a REST API
          </span>{" "}
          used by 200 students
        </p>
        <span className="text-ink inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold">
          <ArrowCounterClockwiseIcon className="size-3" />
          Undo
        </span>
      </div>
    </Vignette>
  );
}

/** The Applications page's list, each row's Resume cell naming the resume
 *  it went out with (View Resume, KAN-267). Shared with the tracker page. */
export function SentResumeVisual() {
  const rows = [
    {
      job: matchingFeature.jobs[1],
      status: "Interviewing",
      date: "Oct 1",
      file: "Alex_Morgan_Stripe",
    },
    { job: matchingFeature.jobs[3], status: "Applied", date: "Oct 3", file: "Resume #2" },
    { job: matchingFeature.jobs[4], status: "Applied", date: "Oct 6", file: "Resume #2" },
  ];
  return (
    <Vignette className="px-3">
      <div className="surface-card rounded-2xl p-3">
        <div className="text-ink-muted flex px-2 pb-1.5 text-[10px] font-semibold">
          <span className="flex-1">Role</span>
          <span className="w-[132px]">Resume</span>
        </div>
        <div className="grid gap-1">
          {rows.map(({ job, date, file }, i) => (
            <div
              key={job.id}
              className="flex min-w-0 items-center rounded-xl bg-white px-2 py-1.5 ring-1 ring-slate-900/5"
            >
              <span className="flex min-w-0 flex-1 items-center gap-2">
                <FaviconLogo domain={job.domain} className="size-7" />
                <span className="min-w-0">
                  <span className="text-ink block truncate text-[11px] font-semibold">
                    {job.title}
                  </span>
                  <span className="text-ink-meta block text-[10px]">
                    {job.company} · {date}
                  </span>
                </span>
              </span>
              <span
                className={cn(
                  "text-ink w-[132px] shrink-0 truncate rounded-lg px-2 py-1 text-[10px] font-semibold ring-1 ring-inset",
                  i === 0 ? "bg-advanced-tint ring-advanced/40" : "ring-slate-900/10",
                )}
              >
                {file}
              </span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-ink-muted mt-3 text-center text-[11px] font-semibold">
        Sent to {followedJob.company} on Oct 1
      </p>
    </Vignette>
  );
}
