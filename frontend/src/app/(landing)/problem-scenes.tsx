import {
  ArrowClockwiseIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  CaretDownIcon,
  CheckCircleIcon,
  DesktopIcon,
  DownloadSimpleIcon,
  FileTextIcon,
  FolderSimpleIcon,
  ListIcon,
  LockSimpleIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  PlusIcon,
  TableIcon,
  TrayIcon,
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
 * **A picture is 20rem wide and at most 319px tall as drawn**: the stage's
 * height and the picture's three sizes are worked out from that
 * (`.problem-window` in landing.css), so a taller one is cut at the
 * stage's foot. Measure after a change.
 *
 * Each plays once as it shows, its parts coming in
 * one after another (the `.journey-*` classes, held by the stage's
 * `data-arrived`), and is drawn finished without script and with reduced
 * motion. All are `aria-hidden`: the problem beside them says what they
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
      <div className="problem-window @container relative w-full max-w-[20rem] min-w-0">
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
 * Four company job boards, each on the hiring system that company is on in
 * scraper/boards.csv (Stripe on Greenhouse, Nike on Workday, Spotify on
 * Lever, Goldman Sachs on Oracle), with that board's own address. All four
 * are in the logo strip. The roles, places and dates are made up; `stale`
 * marks a posting that has sat open for months.
 */
const BOARDS = [
  {
    company: followedJob.company,
    domain: followedJob.domain,
    url: "job-boards.greenhouse.io/stripe",
  },
  { company: "Nike", domain: "nike.com", url: "nike.wd1.myworkdayjobs.com/nke" },
  { company: "Spotify", domain: "spotify.com", url: "jobs.lever.co/spotify" },
  {
    company: "Goldman Sachs",
    domain: "goldmansachs.com",
    url: "hdpc.fa.us2.oraclecloud.com/LateralHiring",
  },
];

type Role = { title: string; place: string; age: string; stale?: boolean };

const GREENHOUSE_ROLES: Role[] = [
  { title: followedJob.title, place: "San Francisco, CA · Hybrid", age: "3 weeks ago" },
  { title: "Staff Engineer, Payments", place: "Seattle, WA", age: "4 months ago", stale: true },
  { title: "Backend Engineer, Billing", place: "Remote, US", age: "6 months ago", stale: true },
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
const LEVER_ROLES: Role[] = [
  {
    title: "Backend Engineer, Playlists",
    place: "New York · Full-time",
    age: "5 months ago",
    stale: true,
  },
  { title: "Data Scientist, Podcasts", place: "London · Full-time", age: "2 days ago" },
  {
    title: "Engineering Manager, Ads",
    place: "Remote · Full-time",
    age: "1 year ago",
    stale: true,
  },
];
const ORACLE_ROLES: Role[] = [
  { title: "Analyst, Global Markets", place: "New York, NY", age: "Posted Jun 12", stale: true },
  { title: "Associate, Software Engineering", place: "Dallas, TX", age: "Posted Nov 18" },
  {
    title: "Analyst, Asset Management",
    place: "Salt Lake City, UT",
    age: "Posted Jul 3",
    stale: true,
  },
  {
    title: "Associate, Risk Engineering",
    place: "Jersey City, NJ",
    age: "Posted Aug 27",
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
 * One tab's page: shown in its tab's turn (`.board-turn` in landing.css).
 * **All four keep one rhythm**: 12px of room, a 24px head (`BoardHead`),
 * then a body that ends about 20px above the window's foot. Drawn to
 * their own heights, two pages ended 40px short and read as unfinished
 * beside the two that filled the window.
 */
function BoardPage({ turn, children }: { turn: number; children: ReactNode }) {
  return (
    <div
      className="board-turn absolute inset-0 px-4 pt-3"
      data-first={turn === 0 || undefined}
      style={{ "--i": turn } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** A board's head: the company's logo, then what that system puts beside
 *  it (its name, a search, filters), in one 24px row. */
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
 * Jobs scattered everywhere: one browser, four company job boards, each on a
 * different hiring system and each laid out its own way. The tabs take
 * turns: the lit tab, the address and the page under it change together,
 * every 3.2 s, round and round (the user's ask, 2026-11-21: "switching
 * through tabs like a company website or a job board"). Each page shows
 * three or four postings as that system lays them out (a department's
 * list, a search with results, filters over postings, a grid of tiles),
 * where six bare text rows read as a table and not a job page (the user's
 * catch). Some postings on every page are months old, in amber.
 *
 * The four differ in layout alone: the type is `T`'s on every one (the
 * comment there).
 *
 * The turns are CSS on opacity alone, on one clock, so the three parts of
 * a turn cannot drift; held while the stage waits to arrive and while none
 * of the picture is on screen (`HoldOffscreen`), and still on the first
 * board with reduced motion.
 */
export function BoardsScene() {
  return (
    <Window>
      <HoldOffscreen className="board-tabs">
        <div className="flex items-end gap-0.5 bg-slate-900/[0.07] pt-2 pr-2 pl-3">
          <Dots lights className="mr-2 mb-2.5" />
          {BOARDS.map((board, i) => (
            <span
              key={board.domain}
              className="journey-in relative flex min-w-0 flex-1 items-center gap-1 px-1 py-1.5"
              style={delay(0.15 + i * 0.12)}
            >
              <span
                className="board-turn absolute inset-0 rounded-t-lg bg-white"
                data-first={i === 0 || undefined}
                style={{ "--i": i } as CSSProperties}
              />
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
        <div className="relative h-[14rem]">
          {/* Greenhouse: the company's name, then each department's roles,
              a hairline between them and the age at the row's end. */}
          <BoardPage turn={0}>
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
          {/* Workday: a search, a count of results, then each result as a
              card, a pin by its place and its posted date on the same line. */}
          <BoardPage turn={1}>
            <BoardHead board={1}>
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
                  <MapPinIcon weight="fill" className="text-ink-meta size-3 shrink-0 opacity-70" />
                  <span className={cn(T.meta, "truncate")}>{role.place}</span>
                  <Age role={role} className="ml-auto" />
                </span>
              </div>
            ))}
          </BoardPage>
          {/* Lever: filters beside the name, then a team's postings, each
              with its place, its age and an Apply at the row's end. */}
          <BoardPage turn={2}>
            <BoardHead board={2}>
              <span className={T.title}>{BOARDS[2].company}</span>
              <span className="ml-auto flex gap-1">
                {["Location", "Team"].map((filter) => (
                  <Field key={filter} className="gap-0.5">
                    {filter}
                    <CaretDownIcon weight="fill" className="size-2 shrink-0 opacity-70" />
                  </Field>
                ))}
              </span>
            </BoardHead>
            <BoardLabel>Engineering</BoardLabel>
            {LEVER_ROLES.map((role) => (
              <div
                key={role.title}
                className={cn(RULE, "flex h-[46px] items-center gap-3 border-b last:border-b-0")}
              >
                <span className="min-w-0 flex-1">
                  <span className={cn(T.title, "block truncate")}>{role.title}</span>
                  <span className="flex gap-1">
                    <span className={cn(T.meta, "truncate")}>{role.place} ·</span>
                    <Age role={role} />
                  </span>
                </span>
                <span className={cn(T.button, FIELD, "text-ink-muted shrink-0 px-2 py-1")}>
                  Apply
                </span>
              </div>
            ))}
          </BoardPage>
          {/* Oracle: a keyword and a place to search by, then a grid of
              tiles, each a posting. */}
          <BoardPage turn={3}>
            <BoardHead board={3}>
              <Field className="flex-1">
                <MagnifyingGlassIcon className="size-3 shrink-0" />
                <span className="truncate">Keyword</span>
              </Field>
              <Field className="w-[5.25rem]">
                <MapPinIcon className="size-3 shrink-0" />
                <span className="truncate">Location</span>
              </Field>
            </BoardHead>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              {ORACLE_ROLES.map((role) => (
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
        </div>
      </HoldOffscreen>
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

/** A file window's sidebar: the usual places, and the folder that is open. */
const PLACES = [
  { name: "Desktop", icon: DesktopIcon },
  { name: "Documents", icon: FileTextIcon },
  { name: "Downloads", icon: DownloadSimpleIcon },
  { name: "Resumes", icon: FolderSimpleIcon },
];

const FILE_ROW = "grid grid-cols-[minmax(0,1fr)_2.75rem] items-center";

/** The resume you keep rewriting: a file window open on the folder of
 *  resume versions, one more saved each time, the newest selected. The
 *  count of items is in the bar at the window's foot, where a file window
 *  keeps it, not beside the title. */
export function ResumesScene() {
  return (
    <Window>
      <div className={cn(RULE, "flex items-center gap-2 border-b bg-slate-900/[0.03] px-3 py-2")}>
        <Dots lights />
        <FolderSimpleIcon weight="fill" className="ml-1.5 size-4 shrink-0 text-[#3b9cf5]" />
        <span className={T.title}>Resumes</span>
      </div>
      {/* On a window narrower than its drawn 20rem (a phone, a small
          laptop) the sidebar goes, so the file names still show whole. */}
      <div className="grid @[19.5rem]:grid-cols-[6rem_minmax(0,1fr)]">
        <div className={cn(RULE, "hidden border-r bg-slate-900/[0.03] px-1 py-2 @[19.5rem]:block")}>
          {/* Sentence case, as a file window sets its sidebar's heading. */}
          <p className={cn(T.meta, "px-1.5 pb-1 font-semibold")}>Favorites</p>
          {PLACES.map(({ name, icon: Icon }) => (
            <p
              key={name}
              className={cn(
                T.meta,
                "text-ink-muted flex items-center gap-1 rounded-md px-1.5 py-1",
                name === "Resumes" && "bg-slate-900/[0.08]",
              )}
            >
              <Icon weight="fill" className="size-3 shrink-0 text-[#3b9cf5]" />
              <span className="truncate">{name}</span>
            </p>
          ))}
        </div>
        <div>
          <div className={cn(FILE_ROW, T.meta, RULE, "border-b px-3 py-1")}>
            <span>Name</span>
            <span>Modified</span>
          </div>
          <ul className="px-1.5 py-1">
            {FILES.map((file, i) => {
              const last = i === FILES.length - 1;
              return (
                <li
                  key={file.name}
                  className={cn(
                    "journey-in rounded-md px-1.5 py-1.5",
                    FILE_ROW,
                    last && "bg-[#2563eb]",
                  )}
                  style={delay(0.2 + i * 0.16)}
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <FileTextIcon
                      weight="fill"
                      className={cn("size-4 shrink-0", last ? "text-white" : "text-danger")}
                    />
                    <span className={cn(T.text, "truncate", last && "text-white")}>
                      {file.name}
                    </span>
                  </span>
                  <span className={cn(T.meta, last && "text-white/85")}>{file.date}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <p className={cn(T.meta, RULE, "flex border-t px-3 py-1")}>
        <span className="truncate">Documents › Job search › Resumes</span>
        <span className="ml-auto shrink-0">{FILES.length} items</span>
      </p>
    </Window>
  );
}

/** A hiring system's steps to apply, the second open. */
const STEPS = ["Account", "My information", "Experience", "Questions"];

/** A required field's mark. */
const Star = () => <span className="text-danger"> *</span>;

/** A form's own blue edge and soft halo on the field in use. */
const FOCUS = { boxShadow: `0 0 0 2px ${LINK_BLUE}, 0 0 0 5px ${LINK_BLUE}26` };

/** The foot of a form's step: a quiet Back and the step's main button,
 *  lit (`on`) or waiting. */
function FormFoot({ next, on }: { next: string; on?: boolean }) {
  return (
    <div className="mt-3 flex items-center justify-between">
      <span className={cn(T.button, "text-ink-meta font-normal")}>Back</span>
      <span
        className={cn(
          T.button,
          "rounded-md px-3 py-1",
          on ? "text-white" : "text-ink-meta/60 bg-slate-900/[0.07]",
        )}
        style={on ? { background: LINK_BLUE } : undefined}
      >
        {next}
      </span>
    </div>
  );
}

/** Forms that ask it all again: one more company's My information step. The
 *  resume is uploaded, and the form asks for what is on it again (the name
 *  done, the email under way), with the forms before it stacked behind. */
export function FormsScene() {
  const [first, ...rest] = candidate.name.split(" ");
  const fields = [
    { label: "First name", value: first },
    { label: "Last name", value: rest.join(" ") },
    { label: "Email", value: `${first.toLowerCase()}.m`, typing: true, wide: true },
    { label: "School", wide: true },
  ];
  return (
    <Window className="p-4" stacked={2}>
      <div className="flex items-center gap-2">
        <FaviconLogo domain={followedJob.domain} className="size-5 rounded-md" />
        <span className={cn(T.title, "truncate")}>Apply for {followedJob.title}</span>
      </div>
      {/* The open step's column is wider, so "My information" shows whole. */}
      <ol className="mt-2.5 grid grid-cols-[1fr_1.4fr_1fr_1fr] gap-1">
        {STEPS.map((step, i) => (
          <li key={step} className="grid gap-1">
            <span
              className="block h-1 rounded-full bg-slate-900/10"
              style={i <= 1 ? { background: LINK_BLUE, opacity: i === 1 ? 0.45 : 1 } : undefined}
            />
            <span className={cn(T.meta, "truncate", i === 1 && "text-ink font-semibold")}>
              {step}
            </span>
          </li>
        ))}
      </ol>
      <p
        className={cn(
          T.meta,
          "journey-in mt-2.5 flex items-center gap-1.5 rounded-md bg-[#e8f5ee] px-2 py-1 text-[#14663c]",
        )}
        style={delay(0.3)}
      >
        <CheckCircleIcon weight="fill" className="size-3.5 shrink-0" />
        <span className="truncate">Resume_FINAL (1).pdf uploaded</span>
      </p>
      <div className="mt-2.5 grid grid-cols-2 gap-x-2.5 gap-y-2">
        {fields.map((field, i) => (
          <div
            key={field.label}
            className={cn("journey-in", field.wide && "col-span-2")}
            style={delay(0.5 + i * 0.12)}
          >
            <p className={T.meta}>
              {field.label}
              <Star />
            </p>
            <span
              className={cn(T.text, FIELD, "mt-1 flex h-6 items-center px-2")}
              style={field.typing ? FOCUS : undefined}
            >
              {field.value}
              {field.typing && <span className="caret-blink bg-ink inline-block h-3 w-px" />}
            </span>
          </div>
        ))}
      </div>
      <FormFoot next="Save and continue" on />
    </Window>
  );
}

/** The questions you dread: one more written question on one more form, its
 *  box empty and the cursor waiting. A "Session expires in 12:48" line
 *  under the box was taken out at the user's ask (2026-11-21). The question
 *  is the one line set a size up (13px): it is what the picture is about. */
export function QuestionScene() {
  return (
    <Window className="p-4">
      <div className="flex items-center gap-2">
        <FaviconLogo domain="notion.so" className="size-5 rounded-md" />
        <span className={T.title}>Apply to Notion</span>
        <span className={cn(T.meta, "ml-auto")}>Question 3 of 5</span>
      </div>
      <span className="mt-2.5 block h-1 rounded-full bg-slate-900/10">
        <span className="block h-full w-3/5 rounded-full" style={{ background: LINK_BLUE }} />
      </span>
      <p className="text-ink mt-3.5 text-[13px] leading-[18px] font-semibold">
        Why do you want to work at Notion?
        <Star />
      </p>
      <p className={cn(T.meta, "mt-0.5")}>In your own words. 500 characters at most.</p>
      <div className="journey-in mt-2 h-24 rounded-lg p-2.5" style={{ ...delay(0.3), ...FOCUS }}>
        <span className="caret-blink bg-ink inline-block h-3.5 w-px" />
      </div>
      <p className={cn(T.meta, "mt-2.5 text-right tabular-nums")}>0 / 500</p>
      <FormFoot next="Next" />
    </Window>
  );
}

/** The applications spreadsheet, eighty rows in, the last ones unsure. */
const ROWS = [
  { n: 78, company: "Ramp", status: "Applied", tone: "blue", resume: "v3", unsure: false },
  { n: 79, company: "Duolingo", status: "Rejected", tone: "red", resume: "?", unsure: true },
  { n: 80, company: "Plaid", status: "No reply", tone: "grey", resume: "v5", unsure: false },
  {
    n: 81,
    company: "Datadog",
    status: "Interview?",
    tone: "amber",
    resume: "FINAL (1)",
    unsure: true,
  },
  { n: 82, company: "Figma", status: "??", tone: "grey", resume: "which one", unsure: true },
  { n: 83, company: "Notion", status: "", tone: "grey", resume: "", unsure: false },
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

const SHEET = "grid grid-cols-[1.75rem_minmax(0,1fr)_5.5rem_5rem]";
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
          {["", "A", "B", "C"].map((letter, i) => (
            <span
              key={letter}
              className={cn(CELL, EDGE, "py-0.5", i === 3 && "border-r-0")}
              style={letter === SELECTED_COLUMN ? EDGE_ON : undefined}
            >
              {letter}
            </span>
          ))}
        </div>
        {/* The sheet's own header row, frozen: a heavier line under it. */}
        <div className={SHEET}>
          <span className={cn(CELL, EDGE, "border-b-slate-900/20")}>1</span>
          {["Company", "Status", "Resume"].map((head, i) => (
            <span
              key={head}
              className={cn(CELL, "border-b-slate-900/20 font-semibold", i === 2 && "border-r-0")}
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
              className={cn(CELL, "truncate border-r-0", row.unsure && "bg-[#fff6cc]")}
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
      <ul>
        {MAIL.map((mail, i) => (
          <li
            key={mail.subject}
            className={cn(
              RULE,
              "journey-in flex gap-2 border-b py-2 pr-3 pl-2 last:border-b-0",
              mail.unread && "bg-slate-900/[0.02]",
            )}
            // The newest comes in last, on top of the others.
            style={delay(i === 0 ? 1.1 : 0.15 + i * 0.15)}
          >
            <span
              className="mt-2.5 size-1.5 shrink-0 rounded-full"
              style={mail.unread ? { background: LINK_BLUE } : undefined}
            />
            <FaviconLogo domain={mail.domain} className="mt-0.5 size-6 rounded-full" />
            <div className="min-w-0 flex-1">
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
          </li>
        ))}
      </ul>
    </Window>
  );
}
