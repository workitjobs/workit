import {
  ArrowClockwiseIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  CaretDownIcon,
  CheckCircleIcon,
  FileTextIcon,
  ListIcon,
  LockSimpleIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  PlusIcon,
  TableIcon,
  TrayIcon,
  UploadSimpleIcon,
} from "@phosphor-icons/react/ssr";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

import { FaviconLogo } from "./favicon-logo";
import { candidate, followedJob } from "./feature-data";
import { HoldOffscreen } from "./hold-offscreen";
import { delay, Panel } from "./scene-parts";

/**
 * The six visuals at the centre of the problems hub (problems.tsx,
 * problem-hub.tsx, KAN-923): one thing a job seeker really sees at each
 * point of a search, drawn at about true size, centred on the hub's flat
 * grey stage. Mock UI of the search as it is, before WorkIt, so nothing
 * here is violet.
 *
 * **Each is the real kind of app it stands for** (the user's ask,
 * 2026-11-21: "Google Sheets or Excel is green at the header"): a green
 * spreadsheet with a formula bar, column letters, a dropdown in each
 * status cell and its sheet tab; a mail
 * inbox with senders' logos and unread dots; a file folder with a sidebar
 * and a blue selected row; a browser with a crowded tab strip and a lock;
 * two application forms with the company's logo, a blue focus ring and a
 * main button. Before, all six were one white window with three grey dots
 * and a bold title, in greys alone, and the section read as boring: the
 * rule above was drawn as "no colour" where it bans only WorkIt's violet.
 * **The colours are each app's own kind** (the constants below) and the
 * hub's only colour, so the open picture is where the eye goes; the cards
 * and the band stay white, ink and grey. **No product's logo or name**: a
 * green sheet reads as a spreadsheet without Google's or Microsoft's mark.
 * **One detail in each tells its card's story**: "Last edit 3 weeks ago",
 * postings months old in amber, the resume uploaded above the fields that
 * ask for it again. The inbox's tray is an outline: filled, it drew as a
 * solid blue block (the user's catch).
 *
 * **A picture is up to 30rem wide and at most 319px tall as drawn**, a
 * window wider than it is tall, as a real one is (it was 20rem until
 * 2026-11-23, and the user found the pictures squished): the stage's size
 * and the picture's sizes are worked out from that (`.problem-window` in
 * landing.css), so a taller one is cut at the stage's foot. Measure after
 * a change. It is fluid down to a phone's 19rem, so every row truncates
 * and every extra column is behind a container query.
 *
 * Each plays once as it shows, its parts coming in
 * one after another (the `.journey-*` classes, held by the stage's
 * `data-arrived`), and is drawn finished without script and with reduced
 * motion. **Three keep moving, because their cards are about doing a
 * thing again and again**: the browser's tabs take turns, the forms take
 * turns and are typed into each time, and the question's box has a stock
 * line typed into it and deleted. All three run the hub's one clock
 * (`--board-loop`) and are held when it is. **A picture's motion says
 * what its card says, or it has none.** All are `aria-hidden`: the problem beside them says what they
 * show. They replaced a clickable frame of three wide screens and, before
 * that, a screening machine, which the user found AI-made: a scan line is a
 * process nobody sees, and these are moments everybody has.
 */

/** Every visual's window: centred on the stage, one width. `stacked`
 *  draws that many more windows peeking out behind it, each a step smaller
 *  and higher: the same thing again and again. */
function Window({
  children,
  className,
  stacked = 0,
}: {
  children: ReactNode;
  className?: string;
  stacked?: number;
}) {
  return (
    <div
      aria-hidden="true"
      // Safe centring: a window taller than a short stage keeps its top in
      // view and is cut at the stage's foot, not at both ends.
      className="absolute inset-0 grid [place-items:safe_center] p-4 sm:p-6"
    >
      {/* On a stage with the room, the visual is drawn up to 1.2 times its
          size, so it leads the hub (`.problem-window` in landing.css, the
          user's ask, 2026-11-21). */}
      <div className="problem-window @container relative w-full max-w-[30rem] min-w-0">
        {Array.from({ length: stacked }, (_, i) => {
          const step = stacked - i;
          return (
            <Panel
              key={step}
              className="journey-in absolute bottom-6"
              style={{
                top: -11 * step,
                left: 14 * step,
                right: 14 * step,
                opacity: 1 - step * 0.2,
              }}
            />
          );
        })}
        <Panel className={cn("journey-in relative w-full overflow-hidden", className)}>
          {children}
        </Panel>
      </div>
    </div>
  );
}

/** The colours of the kinds of app the pictures stand for, none of them
 *  WorkIt's: a spreadsheet's green, a mail app's and a form's blue, a file
 *  list's selection, and amber for what has gone stale. **Amber means one
 *  thing in all six: this has sat too long** (an old posting, a letter
 *  with no reply), so the eye learns it once. */
const SHEET_GREEN = "#1b7f4c";
const LINK_BLUE = "#1a6fd4";
const STALE = "#b45309";

/**
 * The pictures' type: five roles, two weights, one case. Every word in
 * every picture takes one of these and nothing else, so a job's title, a
 * place and a date look the same on all four job boards and in all six
 * pictures.
 *
 * Why (the user's catch, 2026-11-21, "a clash of fonts"): each job board
 * was first drawn in "its own" type. A title was medium on one tab, blue
 * on the next, bold on the third and a size smaller on the fourth; the
 * line under it was sentence case, then Title Case, then tracked capitals;
 * a section label had three looks. The tabs turn every 3.2 s, so the
 * reader saw the type change under the same words again and again.
 * **Set apart by layout, never by type**: each board keeps its own
 * structure (a department's list, a search with results, filters over
 * postings, a grid of tiles) and all four share these roles.
 *
 * - `title`: the name of a thing (a window, a company, a job, a sender).
 * - `text`: a value (a cell, a typed field, a subject line, a file name).
 * - `meta`: what describes it (a place, a date, a count, a hint), in grey.
 * - `label`: a heading over a group, the one role in capitals; at most one
 *   kind of label in a picture.
 * - `button`: a control's word.
 *
 * Two weights, regular and semibold: with medium between them, three
 * weights 100 apart read as an accident, not a hierarchy. Sizes step by
 * about a pixel (10, 10.5, 11, 12), so size never carries a level alone:
 * weight and colour do.
 */
const T = {
  title: "text-ink text-[12px] leading-4 font-semibold",
  text: "text-ink text-[11px] leading-4",
  meta: "text-ink-meta text-[10.5px] leading-[14px]",
  label: "text-ink-meta text-[10px] leading-[14px] font-semibold tracking-[0.05em] uppercase",
  button: "text-[10.5px] leading-4 font-semibold",
};

/** The pictures' lines: one hairline between rows, one edge on a control
 *  (a field, a filter, a quiet button), one corner for each. Six border
 *  greys and four corners had crept in. */
const RULE = "border-slate-900/[0.08]";
const FIELD = "rounded-md ring-1 ring-slate-900/15";

/** Three window dots, as a desktop window's title bar has: grey, or the
 *  red, amber and green of a real one (`lights`). */
function Dots({ lights, className }: { lights?: boolean; className?: string }) {
  const fills = lights ? ["#ff5f57", "#febc2e", "#28c840"] : [];
  return (
    <span className={cn("flex shrink-0 gap-1", className)}>
      {[0, 1, 2].map((dot) => (
        <span
          key={dot}
          className="size-2 rounded-full bg-slate-900/15"
          style={fills[dot] ? { background: fills[dot] } : undefined}
        />
      ))}
    </span>
  );
}

/**
 * The four places a search really has open: two companies' own careers
 * pages, each on the hiring system that company is on in scraper/boards.csv
 * (Stripe on Greenhouse, Nike on Workday), with that board's own address,
 * and two job sites, LinkedIn and Indeed, between them (the user's ask,
 * 2026-11-23: a search is spread over job sites too, not only companies'
 * pages; all four were careers pages). **The two job sites are named, by
 * a tab's favicon and name alone**: the pictures name no other product (a
 * green sheet is a spreadsheet without Google's mark), but "a job site"
 * means nothing without the two every student has open. This is the
 * search before WorkIt: WorkIt reads neither site (docs/job-pipeline.md),
 * and no line says it does. The roles, places and dates are made up, on
 * employers from the logo strip; `stale` marks a posting that has sat
 * open, or been posted again, for weeks.
 */
const BOARDS = [
  {
    company: followedJob.company,
    domain: followedJob.domain,
    url: "job-boards.greenhouse.io/stripe",
  },
  { company: "LinkedIn", domain: "linkedin.com", url: "linkedin.com/jobs/search" },
  { company: "Nike", domain: "nike.com", url: "nike.wd1.myworkdayjobs.com/nke" },
  { company: "Indeed", domain: "indeed.com", url: "indeed.com/jobs?q=software+intern" },
];

type Role = { title: string; place: string; age: string; stale?: boolean; domain?: string };

const GREENHOUSE_ROLES: Role[] = [
  { title: followedJob.title, place: "San Francisco, CA · Hybrid", age: "3 weeks ago" },
  { title: "Staff Engineer, Payments", place: "Seattle, WA", age: "4 months ago", stale: true },
  { title: "Backend Engineer, Billing", place: "Remote, US", age: "6 months ago", stale: true },
];
/** A job site's results: each with its employer's logo, and its age as the
 *  site words it. */
const LINKEDIN_ROLES: Role[] = [
  {
    title: "Software Engineer Intern",
    place: "Figma · New York, NY",
    age: "Promoted",
    domain: "figma.com",
  },
  {
    title: "Technology Intern",
    place: "Capital One · McLean, VA",
    age: "Reposted 5 weeks ago",
    stale: true,
    domain: "capitalone.com",
  },
  {
    title: "Software Engineer, New Grad",
    place: "Datadog · Boston, MA",
    age: "2 months ago",
    stale: true,
    domain: "datadoghq.com",
  },
];
const WORKDAY_ROLES: Role[] = [
  {
    title: "Software Engineer I, Digital",
    place: "Beaverton, OR",
    age: "Posted 30+ days ago",
    stale: true,
  },
  { title: "Data Analyst, Supply Chain", place: "Beaverton, OR", age: "Posted 6 days ago" },
  { title: "Product Manager, Nike App", place: "Remote", age: "Posted 30+ days ago", stale: true },
];
const INDEED_ROLES: Role[] = [
  { title: "Software Engineer Intern", place: "Visa · Austin, TX", age: "Sponsored" },
  {
    title: "Technology Analyst, Entry Level",
    place: "Accenture · Chicago, IL",
    age: "Posted 30+ days ago",
    stale: true,
  },
  { title: "Data Science Intern", place: "Pfizer · New York, NY", age: "Just posted" },
  {
    title: "Junior Software Developer",
    place: "Spotify · Remote",
    age: "Posted 30+ days ago",
    stale: true,
  },
];

/** A posting's age: `meta`, in amber once it has gone stale. */
function Age({ role, className }: { role: Role; className?: string }) {
  return (
    <span
      className={cn(T.meta, "shrink-0", className)}
      style={role.stale ? { color: STALE } : undefined}
    >
      {role.age}
    </span>
  );
}

/**
 * One tab's page, a fifth of the strip that slides (`.board-strip` in
 * landing.css). **All four keep one rhythm**: 12px of room, a 24px head
 * (`BoardHead`), then a body that ends about 20px above the window's foot.
 * Drawn to their own heights, two pages ended 40px short and read as
 * unfinished beside the two that filled the window.
 */
function BoardPage({ children }: { children: ReactNode }) {
  return <div className="px-4 pt-3">{children}</div>;
}

/** A board's head: its own logo, then what that site puts beside it (its
 *  name, a search, filters), in one 24px row. */
function BoardHead({ board, children }: { board: number; children: ReactNode }) {
  return (
    <div className="flex h-6 items-center gap-2">
      <FaviconLogo domain={BOARDS[board].domain} className="size-5 rounded-md" />
      {children}
    </div>
  );
}

/** A heading over a board's postings: the `label` role over a hairline. */
function BoardLabel({ children }: { children: ReactNode }) {
  return <p className={cn(T.label, RULE, "mt-2.5 border-b pb-1")}>{children}</p>;
}

/** A search field or a filter, as a job board draws one. */
function Field({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn(T.meta, FIELD, "flex h-6 min-w-0 items-center gap-1.5 px-2", className)}>
      {children}
    </span>
  );
}

/**
 * Jobs scattered everywhere: one browser, four tabs, two companies' careers
 * pages and two job sites, each laid out its own way. The tabs take turns:
 * the lit tab slides to the next name and the page slides in from the
 * right, as tabs do under a swipe, a quarter of the loop each (the user's
 * asks: tabs that switch, 2026-11-21, and a slide, not a fade,
 * 2026-11-23); the address changes with them. Each page shows three or
 * four postings as that site lays them out (a department's list, results
 * with their employers' logos, a search over result cards, a grid of
 * tiles), where six bare text rows read as a table and not a job page (the
 * user's catch). Some postings on every page are weeks or months old, in
 * amber.
 *
 * The four differ in layout alone: the type is `T`'s on every one (the
 * comment there).
 *
 * The slide is CSS on transforms, on one clock, so the three parts of a
 * turn cannot drift; held while the stage waits to arrive and while none
 * of the picture is on screen (`HoldOffscreen`), and still on the first
 * page with reduced motion.
 */
export function BoardsScene() {
  // The company's name, then each department's roles, a hairline between
  // them and the age at the row's end. Drawn twice: the strip ends on its
  // first page, so the loop goes round without a jump back.
  const greenhouse = (
    <BoardPage>
      <BoardHead board={0}>
        <span className={T.title}>{BOARDS[0].company}</span>
        <span className={T.meta}>Current openings</span>
      </BoardHead>
      <BoardLabel>Engineering</BoardLabel>
      {GREENHOUSE_ROLES.map((role) => (
        <div
          key={role.title}
          className={cn(RULE, "flex h-[46px] items-center gap-3 border-b last:border-b-0")}
        >
          <span className="min-w-0 flex-1">
            <span className={cn(T.title, "block truncate")}>{role.title}</span>
            <span className={cn(T.meta, "block truncate")}>{role.place}</span>
          </span>
          <Age role={role} />
        </div>
      ))}
    </BoardPage>
  );
  return (
    <Window>
      <HoldOffscreen className="board-tabs">
        <div className="flex items-end bg-slate-900/[0.07] pt-2 pr-2 pl-3">
          <Dots lights className="mr-2 mb-2.5" />
          <div className="relative grid min-w-0 flex-1 grid-cols-4">
            {/* The lit tab: one white tab that slides under the names. */}
            <span className="tab-lit rounded-t-lg bg-white" />
            {BOARDS.map((board, i) => (
              <span
                key={board.domain}
                className="journey-in relative flex min-w-0 items-center gap-1 px-1.5 py-1.5"
                style={delay(0.15 + i * 0.12)}
              >
                {/* A bare favicon, as a tab shows one: on a white tile the
                    unlit tabs each read as a button. */}
                <FaviconLogo
                  domain={board.domain}
                  className="relative size-3.5 rounded-[3px] bg-transparent shadow-none"
                />
                <span className={cn(T.meta, "text-ink-muted relative truncate")}>
                  {board.company}
                </span>
              </span>
            ))}
          </div>
        </div>
        <div className={cn(RULE, "text-ink-meta flex items-center gap-2 border-b px-3 py-1.5")}>
          <ArrowLeftIcon className="size-3 shrink-0" />
          <ArrowRightIcon className="size-3 shrink-0 opacity-40" />
          <ArrowClockwiseIcon className="size-3 shrink-0" />
          <span className="bg-well flex h-6 min-w-0 flex-1 items-center gap-1.5 rounded-full px-2.5">
            <LockSimpleIcon weight="fill" className="size-3 shrink-0" />
            <span className="grid min-w-0 flex-1">
              {BOARDS.map((board, i) => (
                <span
                  key={board.domain}
                  className={cn(T.meta, "board-turn col-start-1 row-start-1 truncate")}
                  data-first={i === 0 || undefined}
                  style={{ "--i": i } as CSSProperties}
                >
                  {board.url}
                </span>
              ))}
            </span>
          </span>
        </div>
        <div className="h-[14rem] overflow-hidden">
          <div className="board-strip">
            {greenhouse}
            {/* A job site: a search and its count, then results, each with
                its employer's logo and how long it has been up. */}
            <BoardPage>
              <BoardHead board={1}>
                <Field className="flex-1">
                  <MagnifyingGlassIcon className="size-3 shrink-0" />
                  <span className="text-ink truncate">Software engineer intern</span>
                </Field>
              </BoardHead>
              <BoardLabel>1,204 results</BoardLabel>
              {LINKEDIN_ROLES.map((role) => (
                <div
                  key={role.title}
                  className={cn(
                    RULE,
                    "flex h-[46px] items-center gap-2.5 border-b last:border-b-0",
                  )}
                >
                  <FaviconLogo domain={role.domain ?? ""} className="size-7 rounded-md" />
                  <span className="min-w-0 flex-1">
                    <span className={cn(T.title, "block truncate")}>{role.title}</span>
                    <span className={cn(T.meta, "block truncate")}>{role.place}</span>
                  </span>
                  <Age role={role} />
                </div>
              ))}
            </BoardPage>
            {/* Workday: a search, a count of results, then each result as a
                card, a pin by its place and its posted date on the same line. */}
            <BoardPage>
              <BoardHead board={2}>
                <Field className="flex-1">
                  <MagnifyingGlassIcon className="size-3 shrink-0" />
                  <span className="truncate">Search for jobs or keywords</span>
                </Field>
              </BoardHead>
              <p className={cn(T.label, "mt-2.5")}>214 jobs found</p>
              {WORKDAY_ROLES.map((role) => (
                <div
                  key={role.title}
                  className="mt-1.5 flex h-[42px] flex-col justify-center rounded-lg px-2.5 ring-1 ring-slate-900/[0.08]"
                >
                  <span className={cn(T.title, "block truncate")}>{role.title}</span>
                  <span className="flex items-center gap-1">
                    <MapPinIcon
                      weight="fill"
                      className="text-ink-meta size-3 shrink-0 opacity-70"
                    />
                    <span className={cn(T.meta, "truncate")}>{role.place}</span>
                    <Age role={role} className="ml-auto" />
                  </span>
                </div>
              ))}
            </BoardPage>
            {/* The other job site: what and where to search by, then a grid
                of tiles, each a posting. */}
            <BoardPage>
              <BoardHead board={3}>
                <Field className="flex-1">
                  <MagnifyingGlassIcon className="size-3 shrink-0" />
                  <span className="text-ink truncate">software intern</span>
                </Field>
                <Field className="w-[5.25rem]">
                  <MapPinIcon className="size-3 shrink-0" />
                  <span className="truncate">Where</span>
                </Field>
              </BoardHead>
              <div className="mt-2.5 grid grid-cols-2 gap-2">
                {INDEED_ROLES.map((role) => (
                  <div
                    key={role.title}
                    className="flex h-[76px] min-w-0 flex-col rounded-lg p-2 ring-1 ring-slate-900/[0.08]"
                  >
                    <span className={cn(T.title, "line-clamp-2 h-8")}>{role.title}</span>
                    <span className={cn(T.meta, "truncate")}>{role.place}</span>
                    <Age role={role} />
                  </div>
                ))}
              </div>
            </BoardPage>
            {greenhouse}
          </div>
        </div>
      </HoldOffscreen>
    </Window>
  );
}

/** The newest copy of the resume: the file every form asks for again, and
 *  the one the sheet's Resume column loses track of. */
const RESUME_FILE = "Resume_FINAL (1).pdf";

/** The student's details, the same on every form and at the head of the
 *  resume. The email and the school are the ones Auto Apply's scenes fill
 *  in (features/visuals). */
const [FIRST_NAME, ...LAST_NAMES] = candidate.name.split(" ");
const DETAILS = {
  first: FIRST_NAME,
  last: LAST_NAMES.join(" "),
  email: "alex@example.com",
  school: "Northview University",
  gpa: "3.7",
};

/**
 * The three jobs the resume and the forms pictures go through: the
 * followed job, then a role from Nike's page in the browser picture, then
 * one at Spotify. For each, what its posting asks for, and the resume's
 * skills line and one project bullet as the student rewrites them for it:
 * the same project, told three ways.
 */
const APPLICATIONS = [
  {
    company: followedJob.company,
    domain: followedJob.domain,
    role: followedJob.title,
    file: "Resume_Stripe.docx",
    wants: ["REST APIs", "TypeScript", "Payments"],
    skills: "TypeScript, Node.js, REST APIs, SQL",
    bullet: "Built a budget tracker on a Node.js REST API",
  },
  {
    company: "Nike",
    domain: "nike.com",
    role: WORKDAY_ROLES[0].title,
    file: "Resume_Nike.docx",
    wants: ["React", "E-commerce", "A/B testing"],
    skills: "React, JavaScript, HTML, CSS, Figma",
    bullet: "Built a responsive budget app in React",
  },
  {
    company: "Spotify",
    domain: "spotify.com",
    role: "Backend Engineer, Playlists",
    file: "Resume_Spotify.docx",
    wants: ["Python", "Data pipelines", "SQL"],
    skills: "Python, SQL, pandas, Airflow, Docker",
    bullet: "Wrote a Python pipeline for spending data",
  },
];

/** One of the three jobs' versions of a thing, shown in that job's third
 *  of the loop (`.form-turn` in landing.css); `--i` sets off what is typed
 *  into it. Stacked in one grid cell by the caller. */
function Version({
  turn,
  className,
  children,
}: {
  turn: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn("form-turn col-start-1 row-start-1 min-w-0", className)}
      data-first={turn === 0 || undefined}
      style={{ "--i": turn } as CSSProperties}
    >
      {children}
    </span>
  );
}

/** The highlight on a line the student is rewriting, as a marker's. */
const MARKED = "#fff3bf";

/** A resume line as each job needs it: three versions in one place, each
 *  typed in its job's turn (`.resume-type`, `k` 0 for the first line typed
 *  and 1 for the second), on the marker's yellow. */
function Rewritten({
  pick,
  k,
}: {
  pick: (job: (typeof APPLICATIONS)[number]) => string;
  k: number;
}) {
  return (
    <span className="grid">
      {APPLICATIONS.map((job, i) => {
        const text = pick(job);
        return (
          <Version key={job.company} turn={i} className="bg-white">
            <span
              className={cn(
                T.text,
                "relative block w-fit max-w-full overflow-hidden rounded-[3px] px-1 whitespace-nowrap",
              )}
              style={{ background: MARKED }}
            >
              {text}
              <span
                className="resume-type"
                data-k={k}
                style={{ "--n": text.length, background: "white" } as CSSProperties}
              />
            </span>
          </Version>
        );
      })}
    </span>
  );
}

/** A line of the resume that stays as it is: a grey bar. */
const Line = ({ className }: { className?: string }) => (
  <span className={cn("block h-1.5 rounded-full bg-slate-900/10", className)} />
);

/**
 * The resume you keep rewriting: one resume, open in a word processor
 * beside the job posting, and for each of three jobs its skills line and a
 * project's bullet are typed again in that posting's words; the file's
 * name changes with the job (the user's catch, 2026-11-23: the card is
 * about rewriting one resume for every job's keywords, and the picture was
 * a folder of six saved copies, which is about files). The posting is its
 * own column where the window has the room and one line above the page
 * where it has not. The motion is `.form-turn` and `.resume-type` in
 * landing.css: the three jobs take the loop's thirds.
 */
export function ResumesScene() {
  return (
    <Window>
      <HoldOffscreen>
        <div className={cn(RULE, "flex items-center gap-2 border-b bg-slate-900/[0.03] px-3 py-2")}>
          <Dots lights />
          <FileTextIcon weight="fill" className="ml-1.5 size-4 shrink-0 text-[#3b82f6]" />
          <span className="grid min-w-0 flex-1">
            {APPLICATIONS.map((job, i) => (
              <Version key={job.company} turn={i} className={cn(T.title, "truncate")}>
                {job.file}
              </Version>
            ))}
          </span>
          <span className={cn(T.meta, "shrink-0")}>Edited just now</span>
        </div>
        <div className="grid bg-slate-900/[0.05] @[25rem]:grid-cols-[9.75rem_minmax(0,1fr)]">
          {/* The posting the student is working from, beside the page. */}
          <div className={cn(RULE, "grid border-b bg-white @[25rem]:border-r @[25rem]:border-b-0")}>
            {APPLICATIONS.map((job, i) => (
              <Version
                key={job.company}
                turn={i}
                className="flex items-center gap-2 bg-white px-3 py-2 @[25rem]:block @[25rem]:py-3"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <FaviconLogo domain={job.domain} className="size-5 rounded-md" />
                  <span className={cn(T.title, "truncate")}>{job.company}</span>
                </span>
                <span
                  className={cn(
                    T.meta,
                    "block truncate @[25rem]:mt-1 @[25rem]:line-clamp-2 @[25rem]:whitespace-normal",
                  )}
                >
                  {job.role}
                </span>
                <span className={cn(T.label, "mt-3 hidden @[25rem]:block")}>Looking for</span>
                <ul className="mt-1 hidden gap-1 @[25rem]:grid">
                  {job.wants.map((want) => (
                    <li key={want} className={cn(T.text, "flex items-center gap-1.5")}>
                      <span className="bg-ink-meta size-1 shrink-0 rounded-full" />
                      <span className="truncate">{want}</span>
                    </li>
                  ))}
                </ul>
              </Version>
            ))}
          </div>
          {/* The page: the student's details, then the two lines that
              change for each job among the lines that stay. */}
          <div className="p-3">
            <div className="rounded-[3px] bg-white px-4 py-3 shadow-[0_1px_3px_rgb(15_23_42/0.12)]">
              <p className={cn(T.title, "text-center")}>{candidate.name}</p>
              <p className={cn(T.meta, RULE, "truncate border-b pb-1.5 text-center")}>
                {DETAILS.email} · {DETAILS.school}
              </p>
              <p className={cn(T.label, "mt-2")}>Skills</p>
              <div className="mt-1">
                <Rewritten pick={(job) => job.skills} k={0} />
              </div>
              <p className={cn(T.label, "mt-2.5")}>Projects</p>
              <p className={cn(T.text, "mt-0.5 font-semibold")}>Budget Tracker</p>
              <div className="mt-1">
                <Rewritten pick={(job) => job.bullet} k={1} />
              </div>
              <Line className="mt-1.5 w-4/5" />
              {/* Where the posting is a row above the page (a narrow
                  window), the page ends on its projects, or the window
                  ran past the stage's foot. */}
              <div className="hidden @[25rem]:block">
                <p className={cn(T.label, "mt-2.5")}>Experience</p>
                <p className={cn(T.text, "mt-0.5 font-semibold")}>Teaching Assistant</p>
                <Line className="mt-1.5" />
                <Line className="mt-1.5 w-2/3" />
              </div>
            </div>
          </div>
        </div>
      </HoldOffscreen>
    </Window>
  );
}

/** A required field's mark. */
const Star = () => <span className="text-danger"> *</span>;

/** A form's own blue edge and soft halo on the field in use. */
const FOCUS = { boxShadow: `0 0 0 2px ${LINK_BLUE}, 0 0 0 5px ${LINK_BLUE}26` };

/** One company's form: shown in its turn (`.form-turn` in landing.css),
 *  and `--i` sets off everything done in it. */
function FormPage({ turn, children }: { turn: number; children: ReactNode }) {
  return (
    <div
      className="form-turn absolute inset-0 flex flex-col bg-white"
      data-first={turn === 0 || undefined}
      style={{ "--i": turn } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** A field's box with its value typed in, a letter at a time, in the
 *  field's own stretch of the form's turn (`k`, 0 to 4), under the form's
 *  blue ring while it is typed (`.form-type`, `.form-focus`). */
function Entry({ value, k, className }: { value: string; k: number; className?: string }) {
  return (
    <span className={cn(T.text, FIELD, "relative flex h-6 min-w-0 items-center px-2", className)}>
      <span className="relative block max-w-full min-w-0 overflow-hidden whitespace-nowrap">
        {value}
        <span className="form-type" data-k={k} style={{ "--n": value.length } as CSSProperties} />
      </span>
      <span className="form-focus" data-k={k} style={FOCUS} />
    </span>
  );
}

/** A field with its label above it, as most forms set one. */
function Labelled({
  label,
  value,
  k,
  className,
}: {
  label: string;
  value: string;
  k: number;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <p className={cn(T.meta, "truncate")}>
        {label}
        <Star />
      </p>
      <Entry value={value} k={k} className="mt-0.5" />
    </div>
  );
}

/**
 * The resume, uploaded again on this form: the button to upload it, then
 * the file going up under a bar that fills, then the file, uploaded
 * (`.form-up` in landing.css), all in one place. Every form asks for it,
 * and then for what is on it (the user's ask, 2026-11-23: it was shown as
 * uploaded already, which left out the doing it again).
 */
function Upload({ className }: { className?: string }) {
  const state = "form-up col-start-1 row-start-1 flex min-w-0 items-center gap-1.5 rounded-md px-2";
  return (
    <span className={cn("grid h-6 min-w-0", className)}>
      <span className={cn(T.button, state, "text-ink-muted ring-1 ring-slate-900/15 ring-inset")}>
        <UploadSimpleIcon className="size-3.5 shrink-0" />
        <span className="truncate">Upload resume</span>
      </span>
      <span className={cn(T.meta, state, "bg-slate-900/[0.05]")} data-k={1}>
        <span className="truncate">{RESUME_FILE}</span>
        <span className="ml-auto h-1 w-14 shrink-0 overflow-hidden rounded-full bg-slate-900/10">
          <span
            className="form-up-bar block h-full rounded-full"
            style={{ background: LINK_BLUE }}
          />
        </span>
      </span>
      <span className={cn(T.meta, state, "bg-[#e8f5ee] text-[#14663c]")} data-k={2}>
        <CheckCircleIcon weight="fill" className="size-3.5 shrink-0" />
        <span className="truncate">{RESUME_FILE} uploaded</span>
      </span>
    </span>
  );
}

/** One of the questions every form asks again, with its answer picked in
 *  its turn (`.form-pick`, `k` 0 to 2). */
function Asked({
  question,
  answer,
  k,
  className,
}: {
  question: string;
  answer: "Yes" | "No";
  k: number;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span className={cn(T.meta, "min-w-0 flex-1 truncate")}>
        {question}
        <Star />
      </span>
      {(["Yes", "No"] as const).map((option) => (
        <span
          key={option}
          className={cn(
            T.meta,
            "text-ink-muted relative grid h-5 w-9 shrink-0 place-items-center rounded-full ring-1 ring-slate-900/15 ring-inset",
          )}
        >
          {option}
          {option === answer && (
            <span
              className="form-pick absolute inset-0 grid place-items-center rounded-full font-semibold text-white"
              data-k={k}
              style={{ background: LINK_BLUE }}
            >
              {option}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}

/** A form's main button: waiting, then lit once its last answer is in
 *  (`.form-done`). `fill` is the form's own colour. */
function Submit({ label, fill = LINK_BLUE }: { label: string; fill?: string }) {
  return (
    <span
      className={cn(
        T.button,
        "text-ink-meta/60 relative rounded-md bg-slate-900/[0.07] px-3 py-1 whitespace-nowrap",
      )}
    >
      {label}
      <span
        className="form-done absolute inset-0 grid place-items-center rounded-md text-white"
        style={{ background: fill }}
      >
        {label}
      </span>
    </span>
  );
}

/** A form's five fields: two names, then the email, the school and the
 *  GPA, in three columns where the window has the room and two where it
 *  has not. */
const FIELDS = "grid grid-cols-2 gap-x-2.5 gap-y-1.5 @[25rem]:grid-cols-[1fr_1fr_3.5rem]";

/**
 * Forms that ask it all again: three companies' application forms take
 * turns, and each is filled in while it is up, the same things every
 * time: the resume uploaded again, then the name, the email, the school
 * and the GPA typed in, then the questions every form asks (may you work
 * here, will you need a visa, will you move), answered again (the user's
 * asks, 2026-11-23). Three forms in three layouts, as three hiring systems
 * set them (labels above the fields; a stepped form; labels beside the
 * fields), since the card's point is a new form for every company; the
 * type is `T`'s on all three, as on the browser's four pages. The forms
 * before are stacked behind.
 *
 * It was one still form with the email half typed ("alex.m"), which read
 * as a broken picture and showed one form where the point is many.
 * The motion is `.form-*` in landing.css. The third question shows only
 * where the window is wide: a narrow one sets the fields in more rows.
 */
export function FormsScene() {
  const [stripe, nike, spotify] = APPLICATIONS;
  return (
    <Window className="p-4" stacked={2}>
      <HoldOffscreen className="relative h-[17.5rem]">
        {/* Labels above the fields, one button at the foot. */}
        <FormPage turn={0}>
          <div className="flex items-center gap-2">
            <FaviconLogo domain={stripe.domain} className="size-5 rounded-md" />
            <span className={cn(T.title, "truncate")}>Apply for {stripe.role}</span>
          </div>
          <Upload className="mt-2" />
          <div className={cn(FIELDS, "mt-2")}>
            <Labelled label="First name" value={DETAILS.first} k={0} />
            <Labelled
              label="Last name"
              value={DETAILS.last}
              k={1}
              className="@[25rem]:col-span-2"
            />
            <Labelled
              label="Email"
              value={DETAILS.email}
              k={2}
              className="col-span-2 @[25rem]:col-span-1"
            />
            <Labelled label="School" value={DETAILS.school} k={3} />
            <Labelled label="GPA" value={DETAILS.gpa} k={4} />
          </div>
          <div className="mt-2 grid gap-1">
            <Asked question="Authorized to work in the US?" answer="Yes" k={0} />
            <Asked question="Will you need visa sponsorship?" answer="No" k={1} />
            <Asked
              question="Willing to relocate?"
              answer="Yes"
              k={2}
              className="hidden @[25rem]:flex"
            />
          </div>
          <div className="mt-auto flex justify-end">
            <Submit label="Submit application" />
          </div>
        </FormPage>
        {/* A stepped form: the same things under other labels. */}
        <FormPage turn={1}>
          <div className="flex items-center gap-2">
            <FaviconLogo domain={nike.domain} className="size-5 rounded-md" />
            <span className={cn(T.title, "truncate")}>{nike.role}</span>
            <span className={cn(T.meta, "ml-auto shrink-0")}>Step 2 of 4</span>
          </div>
          <span className="mt-2 grid grid-cols-4 gap-1">
            {[0, 1, 2, 3].map((step) => (
              <span
                key={step}
                className="block h-1 rounded-full bg-slate-900/10"
                style={
                  step <= 1 ? { background: LINK_BLUE, opacity: step === 1 ? 0.45 : 1 } : undefined
                }
              />
            ))}
          </span>
          <Upload className="mt-2" />
          <div className={cn(FIELDS, "mt-2")}>
            <Labelled label="Legal first name" value={DETAILS.first} k={0} />
            <Labelled
              label="Legal last name"
              value={DETAILS.last}
              k={1}
              className="@[25rem]:col-span-2"
            />
            <Labelled
              label="Email address"
              value={DETAILS.email}
              k={2}
              className="col-span-2 @[25rem]:col-span-1"
            />
            <Labelled label="University" value={DETAILS.school} k={3} />
            <Labelled label="GPA" value={DETAILS.gpa} k={4} />
          </div>
          <div className="mt-2 grid gap-1">
            <Asked question="Are you legally able to work in the US?" answer="Yes" k={0} />
            <Asked
              question="Will you require sponsorship?"
              answer="No"
              k={1}
              className="hidden @[25rem]:flex"
            />
          </div>
          <div className="mt-auto flex items-center justify-between">
            <span className={cn(T.button, "text-ink-meta font-normal")}>Back</span>
            <Submit label="Save and continue" />
          </div>
        </FormPage>
        {/* Labels beside the fields, the name asked as one. */}
        <FormPage turn={2}>
          <div className="flex items-center gap-2">
            <FaviconLogo domain={spotify.domain} className="size-5 rounded-md" />
            <span className={cn(T.title, "truncate")}>{spotify.role}</span>
            <span className={cn(T.meta, "ml-auto shrink-0")}>{spotify.company}</span>
          </div>
          <div className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5 whitespace-nowrap">
            <span className={T.meta}>
              Resume
              <Star />
            </span>
            <Upload />
            <span className={T.meta}>
              Full name
              <Star />
            </span>
            <Entry value={candidate.name} k={0} />
            <span className={T.meta}>
              Email
              <Star />
            </span>
            <Entry value={DETAILS.email} k={2} />
            <span className={T.meta}>
              Current school
              <Star />
            </span>
            <Entry value={DETAILS.school} k={3} />
            <span className={T.meta}>
              GPA
              <Star />
            </span>
            <Entry value={DETAILS.gpa} k={4} className="w-14" />
          </div>
          <div className="mt-2 grid gap-1">
            <Asked question="Do you need a visa to work here?" answer="No" k={0} />
            <Asked question="Open to relocating?" answer="Yes" k={1} />
          </div>
          <div className="mt-auto flex justify-end">
            <Submit label="Submit" fill="var(--color-ink)" />
          </div>
        </FormPage>
      </HoldOffscreen>
    </Window>
  );
}

/**
 * The stock answer the question picture writes: the kind a chatbot gives
 * to any company's "why us", in pieces, the stock phrases marked `slop`.
 * Nothing in it is about Notion but its name, which is the point.
 */
const STOCK_ANSWER: { text: string; slop?: boolean }[] = [
  { text: "I am" },
  { text: "thrilled", slop: true },
  { text: "to apply for this" },
  { text: "exciting opportunity", slop: true },
  { text: "at Notion. As a" },
  { text: "highly motivated", slop: true },
  { text: "and" },
  { text: "detail-oriented team player", slop: true },
  { text: "with a" },
  { text: "passion for innovation,", slop: true },
  { text: "I am confident that my" },
  { text: "unique blend of skills", slop: true },
  { text: "aligns perfectly with your mission. I" },
  { text: "thrive in fast-paced environments", slop: true },
  { text: "and am eager to" },
  { text: "leverage my expertise", slop: true },
  { text: "to" },
  { text: "drive impactful results.", slop: true },
];
/** The answer word by word, each with its place in the order it comes in. */
const STOCK_WORDS = STOCK_ANSWER.flatMap((piece) =>
  piece.text.split(" ").map((word) => ({ word, slop: piece.slop })),
);
const STOCK_LENGTH = STOCK_ANSWER.map((piece) => piece.text).join(" ").length;

/**
 * The questions you dread: one more written question on one more form, and
 * in its box a whole stock answer, coming in a word at a time as a chatbot
 * writes one, its stock phrases in the slop gradient (`.stream-word` and
 * `.slop-word` in landing.css; the user's ask, 2026-11-23: a full answer
 * that sounds generic, and looks it). The card says a rushed answer sounds
 * like everyone else's; an empty box with a cursor said only that nothing
 * was written, and one typed line said little more. The count under the
 * box is the finished answer's. A "Session expires in 12:48" line went
 * earlier (the user's ask, 2026-11-21). The question is the one line set a
 * size up (13px): it is what the picture is about.
 */
export function QuestionScene() {
  return (
    <Window className="p-4">
      <HoldOffscreen>
        <div className="flex items-center gap-2">
          <FaviconLogo domain="notion.so" className="size-5 rounded-md" />
          <span className={T.title}>Apply to Notion</span>
          <span className={cn(T.meta, "ml-auto")}>Question 3 of 5</span>
        </div>
        <span className="mt-2.5 block h-1 rounded-full bg-slate-900/10">
          <span className="block h-full w-3/5 rounded-full" style={{ background: LINK_BLUE }} />
        </span>
        <p className="text-ink mt-3 text-[13px] leading-[18px] font-semibold">
          Why do you want to work at Notion?
          <Star />
        </p>
        <p className={cn(T.meta, "mt-0.5")}>In your own words. 500 characters at most.</p>
        {/* A narrow window's box cuts the answer's foot, as a text box
            does once it is full. */}
        <div
          className="journey-in mt-2 h-[6.5rem] overflow-hidden rounded-lg px-2.5 py-2"
          style={{ ...delay(0.3), ...FOCUS }}
        >
          <p className={T.text}>
            {STOCK_WORDS.map(({ word, slop }, i) => (
              <span
                // The answer is fixed, so a word's place is a stable key.
                key={i}
                className={cn("stream-word", slop && "slop-word font-semibold")}
                style={{ "--w": i } as CSSProperties}
              >
                {word}{" "}
              </span>
            ))}
          </p>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <span className={cn(T.button, "text-ink-meta font-normal")}>Back</span>
          {/* The count comes in with the answer's last word. */}
          <span
            className={cn(T.meta, "stream-word mr-3 ml-auto tabular-nums")}
            style={{ "--w": STOCK_WORDS.length + 2 } as CSSProperties}
          >
            {STOCK_LENGTH} / 500
          </span>
          <span
            className={cn(T.button, "text-ink-meta/60 rounded-md bg-slate-900/[0.07] px-3 py-1")}
          >
            Next
          </span>
        </div>
      </HoldOffscreen>
    </Window>
  );
}

/** The applications spreadsheet, eighty rows in, the last ones unsure, with
 *  the notes a student leaves themselves where the window has a column for
 *  them. */
const ROWS = [
  {
    n: 78,
    company: "Ramp",
    status: "Applied",
    tone: "blue",
    resume: "v3",
    note: "",
    unsure: false,
  },
  {
    n: 79,
    company: "Duolingo",
    status: "Rejected",
    tone: "red",
    resume: "?",
    note: "auto-reply?",
    unsure: true,
  },
  {
    n: 80,
    company: "Plaid",
    status: "No reply",
    tone: "grey",
    resume: "v5",
    note: "follow up!!",
    unsure: false,
  },
  {
    n: 81,
    company: "Datadog",
    status: "Interview?",
    tone: "amber",
    resume: "FINAL (1)",
    note: "call when??",
    unsure: true,
  },
  {
    n: 82,
    company: "Figma",
    status: "??",
    tone: "grey",
    resume: "which one",
    note: "",
    unsure: true,
  },
  { n: 83, company: "Notion", status: "", tone: "grey", resume: "", note: "", unsure: false },
] as const;

/** The selected cell, C83: the newest row's resume. */
const SELECTED_ROW = 83;
const SELECTED_COLUMN = "C";

/** A status cell's dropdown, as a sheet draws one: a pill in the option's
 *  own colour with a caret at its end (the user's ask, 2026-11-21). The
 *  newest row's is still empty: the caret alone. */
const STATUS_TONES = {
  blue: "bg-[#dbe7fb] text-[#1a4fa0]",
  red: "bg-danger-tint text-danger",
  amber: "bg-warning-tint text-warning",
  grey: "bg-slate-900/[0.07] text-ink-muted",
};

function StatusChip({ status, tone }: { status: string; tone: keyof typeof STATUS_TONES }) {
  return (
    <span
      className={cn(
        "flex h-4 min-w-0 items-center gap-0.5 rounded-full pr-1 pl-1.5 text-[10px] leading-none",
        STATUS_TONES[tone],
      )}
    >
      <span className="truncate">{status}</span>
      <CaretDownIcon weight="fill" className="size-2 shrink-0 opacity-70" />
    </span>
  );
}

/** The sheet's columns: a fourth, Notes, where the window is wide enough. */
const SHEET =
  "grid grid-cols-[1.75rem_minmax(0,1fr)_5.5rem_5rem] @[25rem]:grid-cols-[1.75rem_minmax(0,1fr)_6rem_5.5rem_6.5rem]";
/** The third column's right edge and the fourth column, both only there. */
const THIRD = "border-r-0 @[25rem]:border-r";
const FOURTH = "hidden border-r-0 @[25rem]:block";
const CELL = cn(T.text, RULE, "border-r border-b px-2 py-1");
/** A row's number and a column's letter: the sheet's own grey edge. */
const EDGE = "text-ink-meta bg-slate-900/[0.04] px-0 text-center text-[10px] tabular-nums";
/** The edge beside the selected cell, tinted as a sheet tints it. */
const EDGE_ON = { background: `${SHEET_GREEN}24`, color: SHEET_GREEN };

/** The spreadsheet you gave up on: the student's own sheet, green as a
 *  spreadsheet is, last edited weeks ago; statuses guessed, the resume each
 *  went with unknown, and the newest row's cell selected and empty, its
 *  column's letter and its row's number tinted, as a sheet marks where the
 *  selection is. */
export function TrackerScene() {
  return (
    <Window>
      <div className="flex items-center gap-2 px-3 py-2" style={{ background: SHEET_GREEN }}>
        <span className="grid size-5 shrink-0 place-items-center rounded-[5px] bg-white">
          <TableIcon weight="fill" className="size-3.5" style={{ color: SHEET_GREEN }} />
        </span>
        <span className={cn(T.title, "truncate text-white")}>Job search 2026</span>
        <span className={cn(T.meta, "ml-auto shrink-0 text-white/85")}>Last edit 3 weeks ago</span>
      </div>
      <div className={cn(RULE, "flex items-center gap-2 border-b px-2 py-1")}>
        <span className={cn(T.meta, FIELD, "text-ink-muted w-8 rounded-[3px] text-center")}>
          {SELECTED_COLUMN}
          {SELECTED_ROW}
        </span>
        <span className={cn(T.meta, "font-serif italic")}>fx</span>
        <span className="h-3 w-px bg-slate-900/12" />
      </div>
      <div>
        <div className={SHEET}>
          {["", "A", "B", "C", "D"].map((letter, i) => (
            <span
              key={letter}
              className={cn(CELL, EDGE, "py-0.5", i === 3 && THIRD, i === 4 && FOURTH)}
              style={letter === SELECTED_COLUMN ? EDGE_ON : undefined}
            >
              {letter}
            </span>
          ))}
        </div>
        {/* The sheet's own header row, frozen: a heavier line under it. */}
        <div className={SHEET}>
          <span className={cn(CELL, EDGE, "border-b-slate-900/20")}>1</span>
          {["Company", "Status", "Resume", "Notes"].map((head, i) => (
            <span
              key={head}
              className={cn(
                CELL,
                "border-b-slate-900/20 font-semibold",
                i === 2 && THIRD,
                i === 3 && FOURTH,
              )}
            >
              {head}
            </span>
          ))}
        </div>
        {ROWS.map((row, i) => (
          <div key={row.n} className={cn(SHEET, "journey-in")} style={delay(0.2 + i * 0.12)}>
            <span className={cn(CELL, EDGE)} style={row.n === SELECTED_ROW ? EDGE_ON : undefined}>
              {row.n}
            </span>
            <span className={CELL}>{row.company}</span>
            <span className={cn(CELL, "flex items-center px-1.5")}>
              <StatusChip status={row.status} tone={row.tone} />
            </span>
            <span
              className={cn(CELL, "truncate", THIRD, row.unsure && "bg-[#fff6cc]")}
              // The selected cell, as a sheet outlines it.
              style={
                row.n === SELECTED_ROW ? { boxShadow: `inset 0 0 0 2px ${SHEET_GREEN}` } : undefined
              }
            >
              {row.resume}
              {row.n === SELECTED_ROW && (
                <span className="caret-blink bg-ink inline-block h-3 w-px align-middle" />
              )}
            </span>
            <span className={cn(CELL, "text-ink-meta truncate", FOURTH)}>{row.note}</span>
          </div>
        ))}
      </div>
      <div className="text-ink-meta flex items-center gap-2.5 bg-slate-900/[0.04] px-2.5">
        <PlusIcon className="size-3 shrink-0" />
        <ListIcon className="size-3 shrink-0" />
        <span
          className={cn(T.button, "bg-white px-2.5 py-1")}
          style={{ color: SHEET_GREEN, boxShadow: `inset 0 -2px 0 ${SHEET_GREEN}` }}
        >
          Sheet1
        </span>
      </div>
    </Window>
  );
}

/**
 * The inbox, newest first. **The story is in what a mail app really
 * shows**, with no caption laid over it: the same sender twice a quarter of
 * an hour apart (the application received at 11:32 PM, turned down at
 * 11:47 PM), and the student's own follow-up with the nudge a mail app
 * puts on a letter nobody answered. Two pills, "Minutes after you applied"
 * and "No reply in weeks", said this before; no mail app has such labels,
 * so they read as notes stuck on the picture and broke it (2026-11-21).
 * **The letters arrive one at a time, oldest first**, each opening at the
 * top and pushing the rest down (`.mail-in` in landing.css; the user's
 * ask, 2026-11-23), so the story plays in order: the follow-up nobody
 * answered, a no, an application received, and its no a quarter of an
 * hour later.
 */
const MAIL = [
  {
    from: "Stripe Recruiting",
    domain: "stripe.com",
    subject: "An update on your application",
    preview: "After careful review, we have decided to move forward with other candidates…",
    when: "11:47 PM",
    unread: true,
    nudge: null,
  },
  {
    from: "Stripe Recruiting",
    domain: "stripe.com",
    subject: "Thanks for applying to Stripe",
    preview: `We received your application for ${followedJob.title}…`,
    when: "11:32 PM",
    unread: false,
    nudge: null,
  },
  {
    from: "Datadog Careers",
    domain: "datadoghq.com",
    subject: "Your application to Datadog",
    preview: "Thank you for your interest. Unfortunately…",
    when: "Tue",
    unread: true,
    nudge: null,
  },
  {
    from: "To: Notion Recruiting",
    domain: "notion.so",
    subject: "Following up on my application",
    preview: "Hi, I wanted to check in on the status of my…",
    when: "Oct 28",
    unread: false,
    nudge: "Sent 24 days ago. Follow up?",
  },
];

/** Silence, or an instant no: a mail inbox after a few weeks of applying,
 *  each sender's logo beside its letter. */
export function RepliesScene() {
  const unread = MAIL.filter((mail) => mail.unread).length;
  return (
    <Window>
      <div className={cn(RULE, "flex items-center gap-2 border-b px-3 py-2")}>
        <TrayIcon className="size-4 shrink-0" style={{ color: LINK_BLUE }} />
        <span className={T.title}>Inbox</span>
        <span
          className={cn(T.button, "rounded-full px-1.5 text-[10px] text-white")}
          style={{ background: LINK_BLUE }}
        >
          {unread}
        </span>
        <span
          className={cn(T.meta, "bg-well ml-auto flex h-6 items-center gap-1 rounded-full px-2.5")}
        >
          <MagnifyingGlassIcon className="size-3 shrink-0" />
          Search mail
        </span>
      </div>
      {/* Room for all four from the start, so the window stands still as
          they come in. */}
      <ul className="min-h-[15.75rem]">
        {MAIL.map((mail, i) => (
          <li
            key={mail.subject}
            // The oldest comes in first; each newer one opens above it.
            className={cn(RULE, "mail-in border-b last:border-b-0")}
            style={{ "--order": MAIL.length - 1 - i } as CSSProperties}
          >
            <div className={cn("flex gap-2 pr-3 pl-2", mail.unread && "bg-slate-900/[0.02]")}>
              <span
                className="mt-[1.125rem] size-1.5 shrink-0 rounded-full"
                style={mail.unread ? { background: LINK_BLUE } : undefined}
              />
              <FaviconLogo domain={mail.domain} className="mt-2.5 size-6 rounded-full" />
              <div className="min-w-0 flex-1 py-2">
                <div className="flex items-baseline gap-2">
                  <span className={cn(T.title, "truncate", !mail.unread && "font-normal")}>
                    {mail.from}
                  </span>
                  <span className={cn(T.meta, "ml-auto shrink-0")}>{mail.when}</span>
                </div>
                <p className={cn(T.text, "truncate")}>{mail.subject}</p>
                {mail.nudge ? (
                  <p className={T.meta} style={{ color: STALE }}>
                    {mail.nudge}
                  </p>
                ) : (
                  <p className={cn(T.meta, "truncate")}>{mail.preview}</p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Window>
  );
}
