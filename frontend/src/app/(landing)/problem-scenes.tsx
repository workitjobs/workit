import { FileTextIcon, WarningIcon } from "@phosphor-icons/react/ssr";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { logoStrip } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob } from "./feature-data";
import { delay, Panel } from "./scene-parts";

/**
 * The six visuals at the centre of the problems hub (problems.tsx,
 * problem-hub.tsx, KAN-923): one thing a job seeker really sees at each
 * point of a search, drawn as plain UI at about true size, centred on the
 * hub's flat grey stage. Mock UI of the search as it is, before WorkIt, so
 * nothing here is violet. Each plays once as it shows, its parts coming in
 * one after another (the `.journey-*` classes, held by the stage's
 * `data-arrived`), and is drawn finished without script and with reduced
 * motion. All are `aria-hidden`: the problem beside them says what they
 * show. They replaced a clickable frame of three wide screens and, before
 * that, a screening machine, which the user found AI-made: a scan line is a
 * process nobody sees, and these are moments everybody has.
 */

/** Every visual's window: centred on the stage, one width. */
function Window({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      aria-hidden="true"
      // Safe centring: a window taller than a short stage keeps its top in
      // view and is cut at the stage's foot, not at both ends.
      className="absolute inset-0 grid [place-items:safe_center] p-4 sm:p-6"
    >
      <Panel className={cn("journey-in w-full max-w-[22rem] overflow-hidden", className)}>
        {children}
      </Panel>
    </div>
  );
}

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

/** One company's open roles, as its own job board lists them: every team
 *  and level, some open for months, and the one that fits in among them. */
const ROLES = [
  { title: "Staff Software Engineer, Payments", age: "4 months ago" },
  { title: "Senior Data Scientist, Risk", age: "2 days ago" },
  { title: "Engineering Manager, Billing", age: "6 months ago" },
  { title: followedJob.title, age: "3 weeks ago" },
  { title: "Account Executive, Enterprise", age: "5 months ago" },
  { title: "Solutions Architect", age: "1 year ago" },
];

/** Jobs scattered everywhere: a browser of company job board tabs opening
 *  one after another, the open board listing every role at every level. */
export function BoardsScene() {
  const tabs = logoStrip.employers.slice(0, 4);
  return (
    <Window>
      <div className="flex items-end gap-1 bg-slate-900/[0.04] px-2 pt-2">
        {tabs.map((employer, i) => (
          <span
            key={employer.domain}
            className={cn(
              "journey-in flex min-w-0 flex-1 items-center gap-1.5 rounded-t-md px-2 py-1.5",
              i === 0 && "bg-white",
            )}
            style={delay(0.15 + i * 0.12)}
          >
            <FaviconLogo domain={employer.domain} className="size-4 rounded-[4px] shadow-none" />
            <span className="text-ink-muted truncate text-[11px]">{employer.name} Careers</span>
          </span>
        ))}
        <span
          className="journey-in text-ink-meta shrink-0 px-2 pb-1.5 text-[11px]"
          style={delay(0.7)}
        >
          + more
        </span>
      </div>
      <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 py-2">
        <Dots />
        <span className="bg-well text-ink-meta ml-1 flex-1 truncate rounded-full px-3 py-1 text-[11px]">
          {followedJob.domain}/jobs
        </span>
      </div>
      <div className="px-4 py-3">
        <p className="text-ink text-[13px] font-semibold">Open roles</p>
        <ul className="mt-2">
          {ROLES.map((role, i) => (
            <li
              key={role.title}
              className="journey-in flex items-baseline gap-3 border-t border-slate-900/[0.05] py-1.5"
              style={delay(0.8 + i * 0.07)}
            >
              <span className="text-ink truncate text-[12px]">{role.title}</span>
              <span className="text-ink-meta ml-auto shrink-0 text-[11px]">{role.age}</span>
            </li>
          ))}
        </ul>
      </div>
    </Window>
  );
}

/** The resume, saved again for each job. */
const FILES = [
  { name: "Resume.pdf", date: "Aug 2" },
  { name: "Resume_final.pdf", date: "Sep 14" },
  { name: "Resume_final_v2.pdf", date: "Sep 15" },
  { name: "Resume_Stripe.pdf", date: "Oct 3" },
  { name: "Resume_Figma_NEW.pdf", date: "Oct 9" },
  { name: "Resume_FINAL (1).pdf", date: "Today" },
];

/** A new resume for every job: a folder of resume versions, one more
 *  saved each time, the newest selected. */
export function ResumesScene() {
  return (
    <Window>
      <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 py-2.5">
        <Dots />
        <span className="text-ink ml-1 text-[12px] font-semibold">Applications</span>
        <span className="text-ink-meta ml-auto text-[11px]">{FILES.length} items</span>
      </div>
      <div className="text-ink-meta grid grid-cols-[minmax(0,1fr)_4.5rem] px-3 pt-2 pb-1 text-[10px] font-semibold tracking-[0.06em] uppercase">
        <span>Name</span>
        <span>Modified</span>
      </div>
      <ul className="px-1.5 pb-2">
        {FILES.map((file, i) => {
          const last = i === FILES.length - 1;
          return (
            <li
              key={file.name}
              className={cn(
                "journey-in grid grid-cols-[minmax(0,1fr)_4.5rem] items-center rounded-md px-1.5 py-1.5",
                last && "bg-advanced-tint",
              )}
              style={delay(0.2 + i * 0.16)}
            >
              <span className="flex min-w-0 items-center gap-2">
                <FileTextIcon weight="fill" className="text-danger size-4 shrink-0" />
                <span className="text-ink truncate text-[12px]">{file.name}</span>
              </span>
              <span className="text-ink-meta text-[11px]">{file.date}</span>
            </li>
          );
        })}
      </ul>
    </Window>
  );
}

/** A hiring system's steps to apply, the third open. */
const STEPS = ["Account", "Resume", "My experience", "Questions"];

/** The same form, every time: the resume uploaded, and the form asking for
 *  the work history the resume already holds. */
export function FormsScene() {
  return (
    <Window className="p-4">
      <p className="text-ink truncate text-[13px] font-semibold">Apply for {followedJob.title}</p>
      <ol className="mt-3 grid grid-cols-4 gap-1">
        {STEPS.map((step, i) => (
          <li key={step} className="grid gap-1">
            <span
              className={cn(
                "block h-1 rounded-full",
                i < 2 ? "bg-ink" : i === 2 ? "bg-ink/40" : "bg-slate-900/10",
              )}
            />
            <span
              className={cn(
                "truncate text-[10px]",
                i === 2 ? "text-ink font-semibold" : "text-ink-meta",
              )}
            >
              {step}
            </span>
          </li>
        ))}
      </ol>
      <div
        className="journey-in bg-warning-tint text-warning mt-4 flex items-start gap-2 rounded-lg px-2.5 py-2 text-[11px] leading-snug font-medium"
        style={delay(0.5)}
      >
        <WarningIcon weight="fill" className="mt-px size-3.5 shrink-0" />
        Resume uploaded. Please enter your work experience below.
      </div>
      <div className="mt-3 grid gap-2.5">
        {["Job title", "Company", "Role description"].map((label, i) => (
          <div key={label} className="journey-in" style={delay(0.8 + i * 0.12)}>
            <p className="text-ink-meta text-[10px] font-medium">{label}</p>
            <span
              className={cn(
                "mt-1 block rounded-md ring-1 ring-slate-900/15",
                label === "Role description" ? "h-10" : "h-6",
              )}
            />
          </div>
        ))}
      </div>
    </Window>
  );
}

/** “Why do you want to work here?”: one more written question on one more
 *  form, its box empty, the cursor waiting. */
export function QuestionScene() {
  return (
    <Window className="p-4">
      <div className="flex items-center gap-2">
        <FaviconLogo domain="notion.so" className="size-5 rounded-md" />
        <span className="text-ink text-[12px] font-semibold">Apply to Notion</span>
        <span className="text-ink-meta ml-auto text-[11px]">Question 3 of 5</span>
      </div>
      <p className="text-ink mt-4 text-[13px] font-medium">
        Why do you want to work at Notion? <span className="text-danger">*</span>
      </p>
      <div
        className="journey-in mt-2 h-28 rounded-lg p-2.5 ring-2 ring-slate-900/70"
        style={delay(0.3)}
      >
        <span className="caret-blink bg-ink inline-block h-3.5 w-px" />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="text-ink-meta">Required</span>
        <span className="text-ink-meta tabular-nums">0 / 500</span>
      </div>
    </Window>
  );
}

/** The applications spreadsheet, eighty rows in, the last ones unsure. */
const ROWS = [
  { n: 78, company: "Ramp", status: "Applied", resume: "v3", unsure: false },
  { n: 79, company: "Duolingo", status: "Rejected", resume: "?", unsure: true },
  { n: 80, company: "Plaid", status: "No reply", resume: "v5", unsure: false },
  { n: 81, company: "Datadog", status: "Interview?", resume: "FINAL (1)", unsure: true },
  { n: 82, company: "Figma", status: "??", resume: "which one", unsure: true },
  { n: 83, company: "Notion", status: "", resume: "", unsure: false },
];

const SHEET = "grid grid-cols-[2rem_minmax(0,1fr)_5.5rem_5rem]";
const CELL = "border-b border-r border-slate-900/[0.06] px-2 py-1.5";

/** A tracker that’s never current: the student's own spreadsheet, statuses
 *  guessed and the resume each went with unknown, the newest row empty. */
export function TrackerScene() {
  return (
    <Window>
      <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 py-2.5">
        <Dots />
        <span className="text-ink ml-1 text-[12px] font-semibold">Job search 2026</span>
        <span className="text-ink-meta ml-auto text-[11px]">Sheet1</span>
      </div>
      <div className="text-[11px]">
        <div className={cn(SHEET, "text-ink-meta bg-slate-900/[0.03]")}>
          {["", "Company", "Status", "Resume"].map((head) => (
            <span key={head} className={CELL}>
              {head}
            </span>
          ))}
        </div>
        {ROWS.map((row, i) => (
          <div key={row.n} className={cn(SHEET, "journey-in")} style={delay(0.2 + i * 0.12)}>
            <span className={cn(CELL, "text-ink-meta bg-slate-900/[0.03] tabular-nums")}>
              {row.n}
            </span>
            <span className={cn(CELL, "text-ink")}>{row.company}</span>
            <span
              className={cn(
                CELL,
                row.status === "Rejected" ? "text-danger" : "text-ink",
                row.unsure && "bg-[#fff6cc]",
              )}
            >
              {row.status}
            </span>
            <span
              className={cn(CELL, "text-ink truncate border-r-0", row.unsure && "bg-[#fff6cc]")}
            >
              {row.resume}
              {row.n === 83 && (
                <span className="caret-blink bg-ink inline-block h-3 w-px align-middle" />
              )}
            </span>
          </div>
        ))}
      </div>
    </Window>
  );
}

/** The inbox: a rejection lands minutes after applying, above an older one
 *  and an application that never heard back. */
const MAIL = [
  {
    from: "Stripe Recruiting",
    subject: `Your application to ${followedJob.title}`,
    preview: "After careful review, we have decided to move forward with other candidates…",
    when: "11:47 PM",
    chip: { text: "Minutes after you applied", tone: "bg-danger-tint text-danger" },
  },
  {
    from: "Datadog Careers",
    subject: "An update on your application",
    preview: "Thank you for your interest. Unfortunately…",
    when: "Tue",
    chip: null,
  },
  {
    from: "Notion",
    subject: "We received your application",
    preview: "We will be in touch if your experience matches…",
    when: "Oct 28",
    chip: { text: "No update since", tone: "text-ink-muted bg-slate-900/[0.06]" },
  },
];

/** Turned down, or no reply: the inbox after a week of applying, the
 *  newest rejection coming in on top. */
export function RepliesScene() {
  return (
    <Window>
      <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 py-2.5">
        <Dots />
        <span className="text-ink ml-1 text-[12px] font-semibold">Inbox</span>
      </div>
      <ul>
        {MAIL.map((mail, i) => (
          <li
            key={mail.from}
            className={cn(
              "journey-in border-b border-slate-900/[0.05] px-3 py-2.5 last:border-b-0",
              i === 0 && "bg-slate-900/[0.02]",
            )}
            // The newest comes in last, on top of the others.
            style={delay(i === 0 ? 0.9 : 0.15 + i * 0.15)}
          >
            <div className="flex items-baseline gap-2">
              <span className={cn("text-ink truncate text-[12px]", i === 0 && "font-semibold")}>
                {mail.from}
              </span>
              <span className="text-ink-meta ml-auto shrink-0 text-[11px]">{mail.when}</span>
            </div>
            <p className={cn("text-ink mt-0.5 truncate text-[11.5px]", i === 0 && "font-medium")}>
              {mail.subject}
            </p>
            <p className="text-ink-meta mt-0.5 truncate text-[11px]">{mail.preview}</p>
            {mail.chip && (
              <span
                className={cn(
                  "mt-1.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold",
                  mail.chip.tone,
                )}
              >
                {mail.chip.text}
              </span>
            )}
          </li>
        ))}
      </ul>
    </Window>
  );
}
