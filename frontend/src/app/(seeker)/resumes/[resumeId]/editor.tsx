"use client";

import {
  ArrowDownIcon,
  ArrowUpIcon,
  CloudSlashIcon,
  ScissorsIcon,
  StackIcon,
} from "@phosphor-icons/react/ssr";
import localFont from "next/font/local";
import {
  Suspense,
  use,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentProps,
  type ComponentType,
  type ReactNode,
} from "react";

import { CloseIcon, PencilIcon, PlusIcon, TrashIcon } from "@/components/icons";
import { ASK_SCOUT_LIVE } from "@/components/scout/scout-buttons";
import { closeScout, setScoutOpen, useScout } from "@/components/scout/scout-store";
import { ScoutTakeover } from "@/components/scout/scout-takeover";
import { Skeleton } from "@/components/shadcn/skeleton";
import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { useToast } from "@/components/ui/toast";
import {
  addBullet,
  addSkill,
  getBank,
  type Bank,
  type BankEntry,
  type EntrySection,
} from "@/lib/bank-actions";
import {
  fitToOnePage,
  getChoices,
  renderResumePdf,
  resumeChangedAt,
  saveLine,
  savePageSettings,
  updateChoices,
  type Choices,
  type ChoicesUpdate,
  type EditRendered,
  type PageSettings,
  type planFit,
  type ResumeCopy,
  type RenderBox,
  type RenderedPdf,
  type RenderMeasure,
} from "@/lib/built-resume-actions";
import type { Result } from "@/lib/applicant-call";
import { cn } from "@/lib/cn";
import { markResumesStale } from "@/lib/resumes-stale";

import { DownloadMenu, DownloadNotes, useResumeDownload } from "../download-menu";
import { Assistant } from "./assistant";
import { overText } from "./fit-notice";
import { useZoom, zoomWidth } from "./zoom";
import { TitleHistoryContext, type ApplyName, type TitleHistory } from "./resume-title";
import { Walkthrough, type WalkApi } from "./walkthrough";
import {
  SAMPLE_BANK,
  sampleChoices,
  sampleTicked,
  walkCounts,
  type ChapterId,
} from "./walkthrough-model";
import { Notice } from "@/components/ui/notice";
import {
  addCuts,
  bulletsWithNew,
  customKey,
  shownBullets,
  cutLeft,
  HEADER,
  LINK_FIELDS,
  lineOf,
  NO_CUTS,
  mergeChoices,
  move,
  moveTo,
  orderSwaps,
  printedSections,
  sectionOrderAfter,
  withWording,
  swapsOf,
  typed,
  type Swap,
  type Header,
  type HeaderField,
  type Line,
} from "./model";
import { hideAgain, push, reverseChoices, reverseLine, type Edit, type Step } from "./history";
import { OutlineEntryDialog } from "./outline-entry";
import type { BlockAction, PageOutline } from "./page-handles";
import { outlineOf, sectionStrip, type BlockKind, type OutlineBlock } from "./page-outline";
import {
  afterStrips,
  boxKey,
  type Gap,
  kindLabel,
  loadPdfjs,
  PageSkeleton,
  PdfPages,
  type Strip,
} from "./pdf-pages";
import {
  DEFAULT_PAGE,
  companyLeads,
  degreeLeads,
  FONTS,
  FormatOptions,
  SidePanel,
  sizeOf,
  textRoleOf,
} from "./page-format";
import { PHONE_FIELD, PhoneEditor, usePhone } from "./phone";
import { HeaderPanel } from "./header-panel";
import { SectionsOutline } from "./sections-panel";
import { SLIM_BAR } from "./slim-bar";
import {
  Bar,
  ReviewButtons,
  type HistoryTools,
  type LineHandlers,
  type MoveTools,
  type Crumb,
  PanelTabs,
  type PanelTab,
  type Side,
} from "./toolbar";
import { readMarked, runs, showMarked } from "./text-marks";
import {
  cardsOf,
  editKey,
  linesOf,
  marksOf,
  reverted,
  revertAll,
  revertOf,
  type RevertTarget,
  wordsBack,
  type SuggestionPopupApi,
  type SuggestionsApi,
  untouched,
  useTailorReview,
} from "./tailor-review";
import { CutPicker, ExperiencesPicker } from "./experiences-picker";
import { keepFitCuts, readFitCuts } from "./fit-cuts";

/**
 * The desktop editor (KAN-218): the built resume's own PDF, edited on the
 * page. Click a line and type: the field over it shows the text at once,
 * and leaving the line (a click away, Enter, Escape) sends it, only when it
 * differs from what the line prints. Each edit is two requests side by side
 * (KAN-391): `renderEdit` renders it from the editor's copy, reading no
 * database, and `saveLine` or `updateChoices` saves it, writing with no
 * read first. Neither waits for the other. The API reads the text, so a
 * bullet becomes this resume's local variant, an entry's typed field
 * changes the bank and the header's the profile, and the browser holds
 * none of those rules. A save that fails puts the saved resume back
 * (`reload`). The field opens on the box's own printed text. The field is set in Latin Modern,
 * the PDF's own font, at the line's size and weight, and opens with the
 * caret where the click landed, so typing starts where the student
 * pointed and wraps where the PDF does. The sticky bar holds the
 * selected line's actions, or the page-count chip and Fit to One Page. Every
 * save bumps one request counter, and a response older than the latest
 * request is dropped, so a slow render never paints over a newer edit.
 * On a phone-width screen the same state is laid out by `PhoneEditor`
 * (KAN-219, ./phone.tsx). The assistant (KAN-221, ./assistant.tsx) opens
 * in Scout's panel from the top bar's Scout (`ScoutTakeover`), or in a
 * sheet on a phone, and acts through the same saves. On Tailor's page
 * (`suggestions`), each change the run made is tinted and has a card in
 * the Suggestions panel beside the page, to undo; an edit of
 * a changed item through `apply` drops that change.
 *
 * THE FIRST PDF STREAMS IN (KAN-368). The page starts the render and hands
 * it over unawaited (`initial`), since the LaTeX compile is the slowest read
 * in the app (0.7 to 1s): the bar, the title and Back draw at once, and the
 * page area alone waits, over a page-shaped skeleton (FirstRenderPane, in a
 * <Suspense>, reads it). Until it lands there is nothing to click (the click
 * targets are the render's boxes, KAN-209), the assistant and Not on
 * This Resume wait too, and a render that fails shows its own error in the page
 * area. pdf.js starts downloading as the editor mounts, so it is ready when
 * the PDF is. An edit's render never loses to the first one: the first is
 * taken only while there is no other.
 */

// The attribute on the parts of the editor a press may land on without
// clearing the selected line
const KEEPS_SELECTION = "data-keeps-selection";

/** The panel's mark while it shows Cut From Resume: Fit's scissors, amber. */
const CUT_MARK = (
  <span className="bg-warning-tint text-warning rounded-control flex size-8 shrink-0 items-center justify-center">
    <ScissorsIcon aria-hidden className="size-4.5" weight="duotone" />
  </span>
);

/** The panel's mark while it shows the Experiences picker: the toolbar
 *  button's glyph, so what opened it is what it wears, and not Scout's. */
const EXPERIENCES_MARK = (
  <span className="bg-brand-tint text-brand rounded-control flex size-8 shrink-0 items-center justify-center">
    <StackIcon aria-hidden className="size-4.5" weight="duotone" />
  </span>
);

/** The walkthrough's line over the entry form, by section (2026-11-18):
 *  what makes a good one, while its chapter runs. */
const ENTRY_TIPS: Partial<Record<EntrySection, string>> = {
  education:
    "Only the school, degree and graduation date are needed. Add a GPA if it is 3.5 or higher.",
  experience:
    "Write 2 or 3 bullets. Start each with a verb and add a number: \u201cCut load time by 30%.\u201d",
  projects:
    "Say what you built, with which tools, and what it did: \u201cBuilt a course planner used by 200 students.\u201d",
};

// Letter is 612 pt wide; field type is set in cqw of the page so it matches
// the PDF's at any width.
const PAGE_WIDTH = 612;
const pt = (points: number) => `${(points / PAGE_WIDTH) * 100}cqw`;

// Latin Modern Roman, the face Tectonic sets Jake's Resume in (GUST Font
// License), subset to Latin; loaded on the editor page only
const latinModern = localFont({
  src: [
    { path: "./fonts/lmroman10-regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/lmroman10-bold.woff2", weight: "700", style: "normal" },
    { path: "./fonts/lmroman10-italic.woff2", weight: "400", style: "italic" },
  ],
  display: "swap",
});

/** Jake's type for each kind of line on this page: its size in points, and
 *  whether it is bold or italic. */
function typeOf(
  kind: string,
  section: string | null,
  page: PageSettings,
  degreeFirst: boolean,
  companyFirst: boolean,
) {
  const size = sizeOf(textRoleOf(kind, section, degreeFirst, companyFirst), page);
  // \scshape has no bold small capitals in Latin Modern, so the name prints bold
  if (kind === "full_name") return { size, bold: true, italic: false };
  // Degree First prints the school on the degree's row, in its italic, and
  // Company First a job's role on the company's
  const under = degreeFirst || companyFirst;
  if (kind === "title") return { size, bold: !under, italic: under };
  // Company First prints the company on the title's row, bold and upright
  if (kind === "organization") return { size, bold: companyFirst, italic: !companyFirst };
  // A project's tools line (KAN-738) is \textit{\small ...}, the body's size
  if (kind === "tools") return { size, bold: false, italic: true };
  // Education's location is the heading's right slot, upright, and so is
  // the header's (KAN-436), which has no section
  if (kind === "location")
    return {
      size,
      bold: false,
      // on the title's row (Education's, or a job's under Company First), upright
      italic: section !== null && section !== "education" && !companyFirst,
    };
  return { size, bold: false, italic: false };
}

// Where a field's first baseline sits below its top, in ems: Latin Modern's
// ascent (1.127) less half the leading its line height takes from its 1.417
// em content area. A box's top is its first baseline less ASCENT (the API's
// resume_render), more for the name.
const LINE_HEIGHT = 1.2;
const fieldBaseline = (lineHeight: number) => 1.127 - (1.417 - lineHeight) / 2;
const boxAscent = (kind: string) => (kind === "full_name" ? 21 : 8);

/** The open line's field: a bullet's is a rich one, the others plain. */
type LineField = HTMLInputElement | HTMLTextAreaElement | HTMLDivElement;

/** How the open line's field is outlined. The ring alone: a shadow read as a
 *  soft second edge under the line. 1.5px: at 2px the user found it too thick
 *  over the page's fine type. */
/** Where Jake's page draws a bullet's dot against its text, in points:
 *  its centre left of the text and under the line's top, and its width,
 *  read from the dot's own pixels on the PDF (2026-11-19). A scan that
 *  counted only the dark middle of each pixel row gave 8.26, 5.4 and 1.9:
 *  a dot a third too small, 0.55pt high. Measure a dot that is not an
 *  entry's first bullet: the line over that one reaches into its rows. */
const DOT_LEFT = 8.06;
const DOT_DOWN = 5.95;
const DOT_SIZE = 2.7;

const FIELD_RING =
  "ring-brand resize-none overflow-hidden rounded-[2px] ring-[1.5px] outline-none field-sizing-content";

/** Lines that wrap: typed in a field as wide as the text column. A
 *  project's tools line does not: it is a heading's row, a tabular's `l`
 *  column, which never wraps, as an organization's does not. */
const WRAPS = new Set(["bullet", "coursework", "honors"]);

const DEFAULT_WRAPPED_LINE = 12;

// A box reaches 8 pt above its first baseline and 3 pt below its last, and
// wrapped lines sit `wrappedLine` pt apart (the API's resume_render ASCENT,
// DESCENT and the render's `wrapped_line`): how many lines a box covers, as
// its `box_lines` counts them
const boxLines = (box: RenderBox, wrappedLine: number) =>
  1 + Math.max(0, Math.round((box.y1 - box.y0 - 11) / wrappedLine));

type Draft = { key: string; text: string };

/** The page's render of the PDF, as renderResumePdf answers it. It never
 *  rejects: a failure is its `error`. */
type FirstRender = ReturnType<typeof renderResumePdf>;

/** The API refused the edit (a resume or item not found, a line it cannot
 *  read): sent again it answers the same. */
const refused = (status: number | null) => status === 404 || status === 422;

/** A save that failed leaves the page unlike the database, unless the
 *  render refused the edit too. Only a 422 is sure to: both read the line
 *  the same way. A 404 can be the save's alone, since the render reads the
 *  editor's copy and the save the database: an entry deleted in another
 *  tab still renders here. */
const unsaved = (status: number | null) => status !== 422;

/** How long a failed render waits before it is sent once more. */
const RETRY_AFTER_MS = 500;

/** Points under a hidden line that close up with it: the space to the next
 *  line within an entry (about 2) and between entries (about 7), never a
 *  section heading's (20 or more). */
const GAP_SPACE = 10;

/** What Fit to One Page measures a render by (KAN-584), or null from an API
 *  a deploy behind, which sends no measure. */
function measureOf(pdf: RenderedPdf): RenderMeasure | null {
  const { page_count, boxes, wrapped_line, points, area, shrinks } = pdf;
  return points && shrinks ? { page_count, boxes, wrapped_line, points, area, shrinks } : null;
}

/** Whether two page settings print alike. */
function samePage(a: PageSettings, b: PageSettings) {
  return (Object.keys(a) as (keyof PageSettings)[]).every(
    (key) => JSON.stringify(a[key]) === JSON.stringify(b[key]),
  );
}

/** The entries, bullets and skills a change hides. */
function hiddenBy(changes: ChoicesUpdate): string[] {
  return [
    ...(changes.entries ?? []).filter((c) => c.shown === false).map((c) => c.entry_id),
    ...(changes.bullets ?? []).filter((c) => c.shown === false).map((c) => c.bullet_id),
    ...(changes.skills ?? []).filter((c) => c.shown === false).map((c) => c.skill_id),
  ];
}

/** Where a hidden skill leaves its line (KAN-584): from its start to the
 *  next skill's start, since each skill's box holds its comma, so the rest
 *  of the line moves left over it. The line's last skill goes from the comma
 *  of the kept skill before it, or that comma would end the line. A skill
 *  broken across two lines waits for the PDF. */
function skillCut(box: RenderBox, boxes: RenderBox[], gone: Set<string>, line: number): Gap[] {
  if (box.y1 - box.y0 > line * 1.5) return [];
  const row = boxes
    .filter((b) => b.kind === "skill" && b.page === box.page && Math.abs(b.y0 - box.y0) < 1)
    .sort((a, b) => a.x0 - b.x0);
  const at = row.indexOf(box);
  const band = { page: box.page, top: box.y0, bottom: box.y1 };
  const next = row[at + 1];
  if (next) return [{ ...band, x0: box.x0, x1: next.x0 }];
  const kept = row.slice(0, at).findLast((b) => !gone.has(b.item_id));
  if (!kept?.text.endsWith(",")) return [{ ...band, x0: box.x0, x1: box.x1 }];
  const comma = ((kept.x1 - kept.x0) / kept.text.length) * 0.55;
  return [{ ...band, x0: kept.x1 - comma, x1: box.x1 }];
}

/** Whether a change changes anything. */
function changesAny(changes: ChoicesUpdate) {
  return Boolean(changes.entries?.length || changes.bullets?.length || changes.skills?.length);
}

/** A step's choice changes with `more` after them: a Fit's cycles, one step. */
function joined(edit: Edit | null, more: ChoicesUpdate): ChoicesUpdate {
  const was = edit && "changes" in edit ? edit.changes : {};
  return {
    entries: [...(was.entries ?? []), ...(more.entries ?? [])],
    bullets: [...(was.bullets ?? []), ...(more.bullets ?? [])],
    skills: [...(was.skills ?? []), ...(more.skills ?? [])],
  };
}

/** One cycle of Fit to One Page (`planFit`) through `/api/resume-fit`, a
 *  route handler, for the reason `renderEdit` gives. */
async function planFitHere(
  resumeId: string,
  plan: Parameters<typeof planFit>[1],
): Promise<Awaited<ReturnType<typeof planFit>>> {
  try {
    const res = await fetch("/api/resume-fit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeId, plan }),
    });
    return await res.json();
  } catch {
    return { data: null, error: "Could not reach the server.", status: null };
  }
}

/** How long a tab stays hidden before its return asks whether the resume
 *  changed elsewhere (`resumeChangedAt`): a quick switch reads nothing. */
const CHECK_AFTER_MS = 5 * 60_000;

/** The editor tabs' channel: each save that lands is announced on it, so
 *  another tab showing the resume reads it again. Only a signal: each tab's
 *  copy stays in its memory and comes from the database. */
const RESUME_CHANNEL = "workit:resume-edits";

/** The bar's line after a save or a render failed and `reload` ran. */
const lostChange = (why: string | null, failed: "saved" | "shown") =>
  `Your last change could not be ${failed}${why ? ` (${why})` : ""}. The page shows your saved resume.`;

/** An edit's render (`renderEdit`, KAN-391) through `/api/resume-edit`, a
 *  route handler: as a server action it waited behind the edit's save,
 *  since Next runs one client's actions one at a time. A failure that is
 *  not a refusal (the network, a compile timed out) is sent once more:
 *  the render writes nothing and reads no database, so the same copy
 *  renders the same page. */
async function renderEdit(
  resumeId: string,
  edit:
    | { line: { item_id: string; kind: string; text: string } }
    | { changes: ChoicesUpdate }
    | { page: PageSettings },
  source?: ResumeCopy,
): Promise<Result<EditRendered>> {
  const body = JSON.stringify({ resumeId, edit, source });
  const send = async (): Promise<Result<EditRendered>> => {
    try {
      const res = await fetch("/api/resume-edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      return (await res.json()) as Result<EditRendered>;
    } catch {
      return { data: null, error: "Could not reach the server.", status: null };
    }
  };
  const first = await send();
  if (first.data || refused(first.status)) return first;
  await new Promise((resolve) => setTimeout(resolve, RETRY_AFTER_MS));
  return send();
}

/** What the last PDF printed beside the resume's own content: its header,
 *  its template and its file name, sent back in every copy, so the API
 *  renders an edit without reading the resume (KAN-391). */
type Printed = Pick<ResumeCopy, "identity" | "template" | "file_name">;

/** What a request's copy is built from: the bank, the choices and what the
 *  last PDF printed (KAN-391). An Undo step keeps one on each side. */
type Held = { bank: Bank; choices: Choices; printed: Printed | null };

/** A block picked as a whole (KAN-920, ./page-outline.ts). */
type Picked = { kind: BlockKind; id: string };

/** A choice change whose compile was skipped for the one after it
 *  (KAN-919): its id, its changes, the lines drawn over the page for it and
 *  its step, all answered by the render that carries it. */
type Carried = {
  id: string;
  changes: ChoicesUpdate;
  lines: string[];
  step: Step<Held, RenderedPdf> | null;
};

function printedBy(pdf: RenderedPdf): Printed | null {
  return pdf.identity
    ? { identity: pdf.identity, template: pdf.template, file_name: pdf.file_name }
    : null;
}

function splitKey(key: string) {
  const dot = key.lastIndexOf(".");
  return { item_id: key.slice(0, dot), kind: key.slice(dot + 1) };
}

/** A bullet typed in on the page (KAN-920, `newBullets`): `key` names it
 *  until the bank gives it an id; `saving` once it has been left. */
type NewBullet = {
  key: string;
  entryId: string;
  anchor: string;
  after: string;
  text: string;
  saving: boolean;
};

/** The new bullets still to draw against a PDF: those it prints are gone,
 *  and one typed after a printed one is drawn under that one. */
function placeNew(list: NewBullet[], printed: (key: string) => string | undefined): NewBullet[] {
  const out: NewBullet[] = [];
  const moved = new Map<string, string>();
  for (const n of list) {
    const id = printed(n.key);
    const anchor = moved.get(n.anchor) ?? n.anchor;
    if (id) moved.set(n.anchor, id);
    else out.push(anchor === n.anchor ? n : { ...n, anchor });
  }
  return out;
}

export function Editor({
  resumeId,
  initial,
  initialBank,
  initialChoices,
  initialHeader,
  phoneBar,
  phoneBack,
  suggestions,
  suggestionPopup,
  heading,
  more,
  original,
  tour = false,
  onTourEnd,
}: {
  resumeId: string;
  /** The first render, started by the page and not awaited. */
  initial: FirstRender;
  initialBank: Bank;
  initialChoices: Choices;
  initialHeader: Header;
  /** Tailor's Suggestions panel, drawn from the run's record and the
   *  editor's state (./tailor-review.tsx). Only Tailor's page passes it, so
   *  only there are changes tinted: a mark with no card to act on would
   *  mean nothing. */
  suggestions?: ComponentType<SuggestionsApi>;
  /** The small card beside a changed line while it is open, as Docs shows a
   *  suggestion beside its text (KAN-499). */
  suggestionPopup?: ComponentType<SuggestionPopupApi>;
  /** The title row (`ResumeTitle`, renamed in place), over the page and the
   *  column beside it; on Tailor's review the step's row with the name in
   *  it (`TailorReviewBar`). */
  heading: ReactNode;
  /** The resume's ⋯ at the title row's end, after Download (`ResumeMenu`:
   *  Rename, Make Primary, Delete; KAN-825), on the editor's own page only:
   *  Tailor's review is a step of a run, not the resume's page. */
  more?: ReactNode;
  /** The resume Tailor started from, read-only, which the toolbar's View
   *  Original sets beside the page in place of the Suggestions panel. */
  original?: ReactNode;
  /** A row the phone layout's header shows under its buttons: the page's
   *  own controls, which the full-screen phone editor would cover. */
  phoneBar?: ReactNode;
  /** The phone arrow's target, when not the page that opened the editor. */
  phoneBack?: ComponentProps<typeof PhoneEditor>["back"];
  /** Start the tour (./walkthrough.tsx) once the first render lands:
   *  onboarding's, on the resume it just made. */
  tour?: boolean;
  /** The tour ended, finished or left. */
  onTourEnd?: () => void;
}) {
  // Null until the first render lands (FirstRenderPane hands it over).
  const [rendered, setRendered] = useState<RenderedPdf | null>(null);
  // What the next request's copy is built from (KAN-391): the bank and
  // choices as the newest answer left them, with the changes on their way
  // merged in, and the header the newest PDF printed. A ref, so a request
  // that waited for the one before reads what that one left, before React
  // has drawn it.
  const held = useRef<Held>({
    bank: initialBank,
    choices: initialChoices,
    printed: null,
  });
  // The newest PDF any render answered, which a step keeps for an instant
  // Undo; newer than `rendered` while a newer request owns the page
  const lastPdf = useRef<RenderedPdf | null>(null);
  // The page's settings (KAN-435), ahead of the PDF: a pick shows in its
  // control at once, and the next edit's copy carries it
  const [page, setPage] = useState(DEFAULT_PAGE);
  const pageNow = useRef(DEFAULT_PAGE);
  // Over the defaults: an API a deploy behind sends none
  const keepPage = useCallback((next?: Partial<PageSettings>) => {
    const whole = { ...DEFAULT_PAGE, ...next };
    pageNow.current = whole;
    setPage(whole);
  }, []);
  const adopt = useCallback(
    (first: RenderedPdf) => {
      held.current.printed ??= printedBy(first);
      lastPdf.current ??= first;
      setRendered((current) => current ?? first);
      keepPage(first.page_settings);
    },
    [keepPage],
  );
  // pdf.js downloads while the server compiles, not after.
  useEffect(() => {
    void loadPdfjs().catch(() => {});
  }, []);
  const [bank, setBank] = useState(initialBank);
  const [header, setHeader] = useState(initialHeader);
  // The header as saved, for an Undo of a link: the page prints a link
  // without "https://" or "www.", so its reverse needs the stored URL
  const headerNow = useRef(initialHeader);
  useEffect(() => {
    headerNow.current = header;
  });
  const [choices, setChoices] = useState(initialChoices);
  // Undo and Redo (./history.ts): the steps, kept in this tab's memory
  const undos = useRef<Step<Held, RenderedPdf>[]>([]);
  const redos = useRef<Step<Held, RenderedPdf>[]>([]);
  const [steps, setSteps] = useState({ undo: 0, redo: 0 });
  const countSteps = useCallback(
    () => setSteps({ undo: undos.current.length, redo: redos.current.length }),
    [],
  );
  // The choices as the API last answered them, and the changes sent since
  const confirmed = useRef(initialChoices);
  const unanswered = useRef(new Map<string, ChoicesUpdate>());
  const changeCount = useRef(0);
  // A Fit to One Page under way: a second press waits for nothing. The
  // state keeps its buttons dim, and the bar on "Fitting to One Page…", from
  // the click to the last cycle: between two cycles nothing is saving, and
  // the button lit up for a moment between each. Undo, Redo and opening a
  // line wait for it too: a later cycle joins the first cycle's step, so an
  // Undo between two cycles left the later hides with no Undo, and planned
  // the next cycle from a page the plan did not expect
  const fitting = useRef(false);
  const [fittingNow, setFittingNow] = useState(false);
  // The editor's renders run one at a time, so each copy holds every
  // edit before it; a copy built while an earlier edit was on its way would
  // print that edit's old text. Saves run one at a time in their own queue
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const saves = useRef<Promise<unknown>>(Promise.resolve());
  // How many jobs the queue has been given, and which of those waiting are a
  // page's settings: a page's compile goes only if no newer page is next
  const jobs = useRef(0);
  const pageJobs = useRef(new Set<number>());
  const skippedPage = useRef(false);
  // The same for choice changes (KAN-919): a change whose next job is
  // another change skips its compile, and that one renders both. Each
  // compile is 4 to 5 s in production, so three quick hides waited for
  // three PDFs in a row. What a skipped change left for the next one
  // (`Carried`), and whether the last change skipped (its PDF is no step's)
  const choiceJobs = useRef(new Set<number>());
  // The section moves of skipped page compiles, drawn until a page lands
  const carriedPages = useRef<string[]>([]);
  const carried = useRef<Carried[]>([]);
  const skippedChoice = useRef(false);
  // Each typed bullet's saved wording, which the render could not know
  const wordings = useRef(new Map<string, { variant_id: string | null; text: string }>());
  // The moves on their way, shown on the page at once (./pdf-pages.tsx)
  const [swaps, setSwaps] = useState<(Swap & { id: string })[]>([]);
  // The hides on their way, closed up on the page at once (KAN-584): the
  // entries and bullets each change hides, by change id
  const [hides, setHides] = useState<{ id: string; items: string[] }[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  // The block picked from its handle on the page or the breadcrumb (KAN-920):
  // a section, an entry or a bullet as a whole, which Option with an arrow
  // moves and Esc climbs from. A line opened for typing clears it
  const [picked, setPicked] = useState<Picked | null>(null);
  // Typed text by box key (KAN-391): the selected line's, and each line
  // left before the PDF that prints it has painted. The page draws it over
  // the line until then, so leaving a line never shows its old text.
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  // How many lines each wrapping draft shows, for the live page's shift
  const [draftLines, setDraftLines] = useState<Record<string, number>>({});
  // Bullets typed in on the page (KAN-920), each drawn under `anchor`, the
  // printed bullet it follows (`after` is that bullet, or the new one typed
  // before it), until the PDF that prints it paints. Kept in a ref too: an
  // Enter and the blur after it read the list before React renders again.
  const [newBullets, setNewBullets] = useState<NewBullet[]>([]);
  const newNow = useRef<NewBullet[]>([]);
  const setNew = useCallback((change: (list: NewBullet[]) => NewBullet[]) => {
    newNow.current = change(newNow.current);
    setNewBullets(newNow.current);
  }, []);
  // Each new bullet's id once the bank has it, by its key, and the adds in
  // order: one waits for the one before, which it may follow
  const newIds = useRef(new Map<string, string>());
  const adding = useRef<Promise<unknown>>(Promise.resolve());
  const newCount = useRef(0);
  const focusedNew = useRef(new Set<string>());
  // What is on its way, by line key or change id, counted: a line's draft
  // and a move's swap stay until the PDF after it lands
  const onTheirWay = useRef(new Map<string, number>());
  const sent = (key: string) => onTheirWay.current.set(key, (onTheirWay.current.get(key) ?? 0) + 1);
  const answered = (key: string) => {
    const left = (onTheirWay.current.get(key) ?? 1) - 1;
    if (left > 0) onTheirWay.current.set(key, left);
    else onTheirWay.current.delete(key);
  };
  // The selected line as of now, for a save that lands after it changed
  const selectedNow = useRef<string | null>(null);
  // The text last sent for each line, so a line reopened and left as it
  // was while its PDF is on its way is not sent twice
  const lastSent = useRef(new Map<string, string>());
  const drop = useCallback(
    (key: string) =>
      setDrafts((d) =>
        key in d ? Object.fromEntries(Object.entries(d).filter(([k]) => k !== key)) : d,
      ),
    [],
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The resume's PDF and Word downloads, here since KAN-258 (../download-menu.tsx)
  const download = useResumeDownload(resumeId);
  // Tailor's changes awaiting review; `apply` reads the newest through a ref
  const [review, setReview] = useTailorReview(resumeId);
  const latestReview = useRef(review);
  useEffect(() => {
    latestReview.current = review;
  });
  // Over one page, the app's toast says so when the editor opens and again
  // when an edit pushes the resume over, with Fit to One Page as its action
  // (./fit-notice.tsx, KAN-258). It goes once the resume fits, or the editor
  // closes. Its words and Fit are read through a ref: the toast is shown
  // only as `over` turns true, never again on each render.
  const over = (rendered?.page_count ?? 1) > 1;
  const toasts = useToast();
  const fitToast = useRef({ message: "", fit: () => {} });
  // Before the effect that shows it, which runs in the same commit
  useEffect(() => {
    fitToast.current = {
      message: rendered ? overText(rendered.page_count, rendered.lines_over) : "",
      fit,
    };
  });
  useEffect(() => {
    if (!over) return;
    const id = toasts.show({
      message: fitToast.current.message,
      action: { label: "Fit to One Page", onClick: () => fitToast.current.fit() },
    });
    return () => toasts.dismiss(id);
  }, [over, toasts]);
  const latest = useRef(0);
  // When the newest edit was sent, for the round trip's measure (`drawn`)
  const started = useRef<number | null>(null);
  const pending = useRef<Draft | null>(null);
  // Where the last press on the pages landed, from their top left (the bar
  // can change height as the line is selected), to put the caret there
  const pages = useRef<HTMLDivElement>(null);
  const pressed = useRef<{ x: number; y: number } | null>(null);
  const placed = useRef<string | null>(null);
  const phone = usePhone();
  // The Suggestions card in focus (its lines outlined), the card of the
  // marked line last clicked, and the phone's Suggestions sheet
  const [focused, setFocused] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  // What Tailor's review sets beside the page, picked on the toolbar: the
  // Suggestions panel, the original resume, or nothing, when the page
  // takes the room
  const [side, setSide] = useState<Side>("suggestions");
  // What the editor shows in Scout's panel (KAN-440): the assistant, or the
  // Experiences picker, opened from the toolbar. The panel shows one at a
  // time, so they share it, and there is no switch in it: the top bar's Scout
  // is the way back, and a switch only took up the panel's top. Closed, it
  // goes back to the assistant, so the top bar's Scout always opens Scout
  const scoutOpen = useScout().open;
  // The side panel's tabs (KAN-586): Sections and Format, one panel with a
  // tab each, opened and closed by the toolbar's one panel button. They were
  // two toolbar buttons, which read as tools when they are views. The tab
  // shown last is the one the button opens again
  const [tab, setTab] = useState<PanelTab>("sections");
  const [panelView, setPanelView] = useState<"scout" | "experiences" | "cut" | PanelTab>(
    "sections",
  );
  const [panelWasOpen, setPanelWasOpen] = useState(scoutOpen);
  if (panelWasOpen !== scoutOpen) {
    setPanelWasOpen(scoutOpen);
    if (!scoutOpen) setPanelView(tab);
  }
  const showScout = useCallback(() => setPanelView("scout"), []);
  const showPanel = (view: "experiences" | "cut" | "format" | "sections") => {
    if (scoutOpen && panelView === view) return setScoutOpen(false);
    setPanelView(view);
    setScoutOpen(true);
  };
  // Tailor's marks on the page: off when so many lines changed that they get
  // in the way of reading it. The changes stay, and so does the panel
  const [showMarks, setShowMarks] = useState(true);
  // The line whose popup the student closed, so it stays closed on that line
  const [closedPopup, setClosedPopup] = useState<string | null>(null);
  /** The toolbar's panel button: the side panel on its last tab, or closed.
   *  Beside the page on Tailor's review, in Scout's panel on the editor's own
   *  page, as the Experiences picker is. */
  const tabbed = (view: unknown): view is PanelTab => view === "sections" || view === "format";
  const panelOpen = suggestions ? tabbed(side) : scoutOpen;
  const togglePanel = () => {
    if (suggestions) return showSide(tabbed(side) ? null : tab);
    if (scoutOpen) return setScoutOpen(false);
    setPanelView(tab);
    setScoutOpen(true);
  };
  const showTab = (next: PanelTab) => {
    setTab(next);
    if (suggestions) showSide(next);
    else setPanelView(next);
  };
  // Open when the editor opens, where the panel docks beside the page
  // (xl up): below, it floats over the page, so it waits for the button
  useEffect(() => {
    if (!suggestions && window.matchMedia("(min-width: 80rem)").matches) setScoutOpen(true);
  }, [suggestions]);
  const showExperiences = () => {
    showPanel("experiences");
  };
  // GETTING STARTED (./walkthrough.tsx, 2026-11-18): opened by `tour` once
  // the first render lands (onboarding's), or by the title row's Take the
  // Tour. Not on Tailor's review, a step of a run. It holds no logic here
  // but its hooks (`walkApi`, below)
  const [walking, setWalking] = useState(false);
  const [walkAsked, setWalkAsked] = useState(false);
  if (tour && !suggestions && rendered && !walkAsked) {
    setWalkAsked(true);
    setWalking(true);
  }
  const [walkChapter, setWalkChapter] = useState<ChapterId | null>(null);
  // Add Experiences' practice examples while the walkthrough shows it to a
  // student with nothing saved: ticked on screen, never sent to the API
  const [sample, setSample] = useState<Choices | null>(null);
  // What Fit to One Page cut, for Cut From Resume: every fit in this tab,
  // kept in sessionStorage (./fit-cuts.ts), so a reload keeps it
  const [cuts, setCuts] = useState(NO_CUTS);
  // The latest list for a fit's queued job, whose closure can predate the
  // fit before it
  const cutsNow = useRef(NO_CUTS);
  // Restored after mount, never in the first render, which must match the
  // server's (it has no sessionStorage)
  useEffect(() => {
    cutsNow.current = readFitCuts(resumeId);
    setCuts(cutsNow.current);
  }, [resumeId]);
  const [zoom, setZoom] = useZoom();
  // The Suggestions panel, sized to the window from wherever its top is
  const fitPanel = useFitToWindow();

  /** Starts a request; the returned check stays true while it is the latest. */
  const begin = useCallback(() => {
    const request = ++latest.current;
    setSaving(true);
    setError(null);
    return () => request === latest.current;
  }, []);

  /** Runs a request after every request before it has answered. */
  const enqueue = useCallback(<T,>(job: () => Promise<T>): Promise<T> => {
    jobs.current += 1;
    const run = queue.current.then(job);
    queue.current = run.catch(() => undefined);
    return run;
  }, []);

  /** Runs a save after every save before it. Saves have their own queue,
   *  beside the renders': a render never waits for a write, nor a write
   *  for a compile. */
  // Each save changes the resume's edited day, which the Resumes page
  // shows, so it marks that list stale: a revalidation here would render
  // this page, PDF and all, again on every edit (lib/resume-revalidate.ts).
  const queueSave = useCallback((job: () => Promise<unknown>) => {
    markResumesStale();
    saves.current = saves.current.then(job).catch(() => undefined);
  }, []);

  /** The choices an answer gave, with the changes still on their way and
   *  the typed wordings saved since. */
  const keepChoices = useCallback((answer: Choices) => {
    confirmed.current = answer;
    let next = answer;
    for (const changes of unanswered.current.values()) next = mergeChoices(next, changes);
    for (const [bullet, saved] of wordings.current)
      next = withWording(next, bullet, saved.variant_id, saved.text);
    held.current.choices = next;
    setChoices(next);
  }, []);

  const keepRendered = useCallback((next: RenderedPdf) => {
    if (next.identity) held.current.printed = printedBy(next);
    setRendered(next);
  }, []);

  /** The copy each request carries, or none before the first PDF. */
  const copy = useCallback((): ResumeCopy | undefined => {
    const { bank, choices, printed } = held.current;
    return printed
      ? {
          entries: bank.entries,
          skills: bank.skills,
          sections: bank.sections,
          choices,
          ...printed,
          page_settings: pageNow.current,
        }
      : undefined;
  }, []);

  /** The choices with the typed wordings saved since (`withWording`). */
  const worded = useCallback((answer: Choices) => {
    let next = answer;
    for (const [bullet, saved] of wordings.current)
      next = withWording(next, bullet, saved.variant_id, saved.text);
    return next;
  }, []);

  /** The editor's state as the last answer left it, without the changes
   *  still on their way: a step's side (./history.ts). */
  const settled = useCallback(
    (): Held => ({
      bank: held.current.bank,
      choices: worded(confirmed.current),
      printed: held.current.printed,
    }),
    [worded],
  );

  /** Records a new step for an edit; a new edit ends what Redo could do. */
  const record = useCallback(
    (redo: Edit): Step<Held, RenderedPdf> => {
      const step: Step<Held, RenderedPdf> = {
        undo: null,
        redo,
        before: null,
        after: null,
        pdfBefore: null,
        pdfAfter: null,
      };
      push(undos.current, step);
      redos.current = [];
      countSteps();
      return step;
    },
    [countSteps],
  );

  /** Drops a step whose edit was refused: there is nothing to undo. */
  const forget = useCallback(
    (step: Step<Held, RenderedPdf>) => {
      undos.current = undos.current.filter((s) => s !== step);
      redos.current = redos.current.filter((s) => s !== step);
      countSteps();
    },
    [countSteps],
  );

  // A rename in the title is a step too (./resume-title.tsx): the title
  // records it and hands over its own rename, which Undo and Redo call
  const applyName = useRef<ApplyName | null>(null);
  const titleHistory = useMemo<TitleHistory>(
    () => ({
      record: (from, to) => {
        const step = record({ name: to });
        step.undo = { name: from };
        return () => forget(step);
      },
      attach: (apply) => {
        applyName.current = apply;
      },
    }),
    [forget, record],
  );

  /**
   * Puts the saved resume back after a save or a render failed, or after it
   * changed elsewhere (KAN-391; `notice` null, quiet):
   * once every save sent before has answered, the bank, the choices and a
   * PDF read from the database replace the editor's copy, and every draft
   * but the selected line's goes. The page showed the edit before it was
   * saved, so this is how a failed write undoes it; after a failed render
   * the save may still have gone through, so only the database can say
   * what the page should show.
   */
  const reload = useCallback(
    // Answers once the read is in, for a caller that acts on the new copy
    (notice: string | null) =>
      enqueue(async () => {
        await saves.current;
        const current = begin();
        const bankRead = await getBank(resumeId);
        const choicesRead = await getChoices(resumeId);
        const pdf = await renderResumePdf(resumeId);
        unanswered.current.clear();
        wordings.current.clear();
        onTheirWay.current.clear();
        // The steps described edits the database no longer holds
        undos.current = [];
        redos.current = [];
        countSteps();
        if (pdf.data) lastPdf.current = pdf.data;
        if (bankRead.data) {
          held.current.bank = bankRead.data;
          setBank(bankRead.data);
        }
        if (choicesRead.data) keepChoices(choicesRead.data);
        setSwaps([]);
        setHides([]);
        const typing = selectedNow.current;
        setDrafts((d) => (typing && typing in d ? { [typing]: d[typing] } : {}));
        if (!current()) return;
        setSaving(false);
        if (pdf.data) keepRendered(pdf.data);
        setError(notice);
      }),
    [begin, countSteps, enqueue, keepChoices, keepRendered, resumeId],
  );

  // Another editor tab's save, or a long time away (KAN-391): `stale` marks
  // a copy to read again once the tab is idle, `hiddenAt` when it hid
  const stale = useRef(false);
  const hiddenAt = useRef<number | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);

  /** Reads a stale copy again, quietly, once the tab shows, no line is open
   *  and no edit is on its way: a reload under an edit would read the
   *  database before that edit's save. Busy, it waits: leaving a line and
   *  each PDF painted (`drawn`) call it again. */
  const refresh = useCallback(() => {
    if (!stale.current || document.hidden) return;
    const busy =
      selectedNow.current !== null || onTheirWay.current.size > 0 || unanswered.current.size > 0;
    if (busy) return;
    stale.current = false;
    reload(null);
  }, [reload]);

  /** Tells the other editor tabs a save landed: `shared` for what every
   *  resume prints (an entry's field, the header), else this resume's only. */
  const announce = useCallback(
    (shared: boolean) => channel.current?.postMessage({ resumeId, shared }),
    [resumeId],
  );

  useEffect(() => {
    const ours =
      typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(RESUME_CHANNEL);
    channel.current = ours;
    if (ours)
      ours.onmessage = (event: MessageEvent<{ resumeId: string; shared: boolean }>) => {
        if (event.data.resumeId !== resumeId && !event.data.shared) return;
        // Hidden, it only marks the copy: ten tabs cost one reload, the one
        // looked at
        stale.current = true;
        refresh();
      };
    const seen = async () => {
      if (document.hidden) {
        hiddenAt.current = Date.now();
        // A save still on its way lands after the tab hid, and is its own
        void saves.current.then(() => {
          if (document.hidden) hiddenAt.current = Date.now();
        });
        return;
      }
      const away = hiddenAt.current;
      hiddenAt.current = null;
      if (stale.current || away === null || Date.now() - away < CHECK_AFTER_MS) return refresh();
      // Another device, or a page that does not announce: one small read
      const { data } = await resumeChangedAt(resumeId);
      if (!data) return;
      // The database's clock read against this one, so a skewed clock
      // neither misses a change nor takes the tab's own saves for one
      const offset = Date.parse(data.now) - Date.now();
      if (Date.parse(data.changed_at) <= away + offset) return;
      stale.current = true;
      refresh();
    };
    document.addEventListener("visibilitychange", seen);
    return () => {
      document.removeEventListener("visibilitychange", seen);
      ours?.close();
      channel.current = null;
    };
  }, [refresh, resumeId]);

  /** Saves a typed line, in the save queue. The answer's bullet variant and
   *  profile go into the editor's state; a failure the render does not
   *  share puts the saved resume back (`unsaved`). */
  const sendLine = useCallback(
    (line: { item_id: string; kind: string; text: string }, source?: ResumeCopy) =>
      queueSave(async () => {
        const { data, error, status } = await saveLine(resumeId, line, source);
        if (data && line.kind === "bullet") {
          wordings.current.set(line.item_id, { variant_id: data.variant_id, text: line.text });
          keepChoices(confirmed.current);
        }
        if (data?.profile) setHeader(data.profile);
        if (data) announce(line.kind !== "bullet");
        if (!data && unsaved(status)) reload(lostChange(error, "saved"));
      }),
    [announce, keepChoices, queueSave, reload, resumeId],
  );

  /** Saves choice changes, in the save queue. */
  const sendChoices = useCallback(
    (changes: ChoicesUpdate) =>
      queueSave(async () => {
        const { error, status } = await updateChoices(resumeId, changes);
        if (!error) announce(false);
        if (error && unsaved(status)) reload(lostChange(error, "saved"));
      }),
    [announce, queueSave, reload, resumeId],
  );

  /** Saves the page's settings, in the save queue. */
  const sendPage = useCallback(
    (settings: PageSettings) =>
      queueSave(async () => {
        const { error, status } = await savePageSettings(resumeId, settings);
        if (error && status !== 404 && status !== 422) reload(error);
      }),
    [queueSave, reload, resumeId],
  );

  /** New page settings: they show in their control at once, the save goes
   *  beside the render, and the page changes when the PDF lands. `record:
   *  false` for an Undo or Redo sent as an edit (`travel`). */
  const applyPage = useCallback(
    async (settings: PageSettings, recorded = true) => {
      const step = recorded ? record({ page: settings }) : null;
      if (step) step.undo = { page: pageNow.current };
      // A section moved shows at once (KAN-920), as an entry's move does: its
      // strip of the page trades places with its neighbours' until the PDF
      // lands. Only the sections that print can move
      const { bank: nowBank, choices: nowChoices } = held.current;
      const printedIn = (order: string[]) =>
        printedSections(nowBank, nowChoices, order).map((s) => s.id);
      const moved = orderSwaps(
        "section",
        printedIn(pageNow.current.section_order),
        printedIn(settings.section_order),
      );
      const id = moved.length ? `page:${++changeCount.current}` : null;
      if (id) {
        sent(id);
        setSwaps((s) => [...s, ...moved.map((m) => ({ ...m, id }))]);
      }
      keepPage(settings);
      sendPage(settings);
      const job = jobs.current + 1;
      pageJobs.current.add(job);
      return enqueue(async () => {
        pageJobs.current.delete(job);
        // Each click on a size or a font is a compile, one at a time, and
        // the next page replaces this one whole, so five quick clicks compile
        // the first and the last. A skipped step keeps no PDF, and neither
        // does the step's before after it: Undo renders those
        if (pageJobs.current.has(job + 1)) {
          skippedPage.current = true;
          // Its section moves stay drawn until the page that replaces it lands
          if (id) carriedPages.current.push(id);
          return;
        }
        const drawnFor = [...carriedPages.current, ...(id ? [id] : [])];
        carriedPages.current = [];
        const current = begin();
        started.current = performance.now();
        if (step) {
          step.before = settled();
          step.pdfBefore = skippedPage.current ? null : lastPdf.current;
        }
        skippedPage.current = false;
        const { data, error } = await renderEdit(resumeId, { page: settings }, copy());
        drawnFor.forEach(answered);
        // Failed, the moves leave the page with the change
        if (!data) setSwaps((s) => s.filter((x) => !drawnFor.includes(x.id)));
        if (data) {
          lastPdf.current = data.render;
          if (step) {
            step.after = settled();
            step.pdfAfter = data.render;
          }
        } else if (step) forget(step);
        if (!current()) return;
        setSaving(false);
        if (!data) return setError(error);
        keepRendered(data.render);
      });
    },
    [begin, copy, enqueue, forget, keepPage, keepRendered, record, resumeId, sendPage, settled],
  );

  /** `record: false` for an Undo or Redo sent as an edit (`travel`). `words`
   *  are lines to draw over the page until the PDF that prints them lands. */
  const apply = useCallback(
    async (
      changes: ChoicesUpdate,
      revertedTarget?: RevertTarget,
      recorded = true,
      words: Record<string, string> = {},
      into?: Step<Held, RenderedPdf>,
      hold?: (pdf: RenderedPdf) => boolean,
    ) => {
      // Its reverse is read before the change shows. `into` is a step this
      // change joins (a Fit's later cycle), keeping the state before its first.
      // A PDF `hold` returns true for is kept but not painted: the page stays
      // as the change left it (a Fit's cycle still over one page)
      const step = into ?? (recorded ? record({ changes }) : null);
      const reverse = step && reverseChoices(held.current.bank, held.current.choices, changes);
      if (into && reverse) {
        into.redo = { changes: joined(into.redo, changes) };
        into.undo = { changes: joined(into.undo, reverse) };
      } else if (step && reverse) step.undo = { changes: reverse };
      // A wording picked from the bar or the assistant replaces what was
      // typed, so the field shows the picked wording, not the old draft
      if (changes.bullets?.some((b) => "variant_id" in b)) {
        pending.current = null;
        const picked = new Set(changes.bullets.map((b) => `${b.bullet_id}.bullet`));
        setDrafts((d) => Object.fromEntries(Object.entries(d).filter(([k]) => !picked.has(k))));
        for (const b of changes.bullets) wordings.current.delete(b.bullet_id);
      }
      // The change shows at once: its plain fields in the choices, and a
      // move as neighbours trading places on the page, one swap at a time
      const id = `change:${++changeCount.current}`;
      const moves = swapsOf(held.current.bank, held.current.choices, changes);
      unanswered.current.set(id, changes);
      keepChoices(confirmed.current);
      sent(id);
      const lines = Object.keys(words);
      lines.forEach(sent);
      setDrafts((d) => ({ ...d, ...words }));
      if (moves.length) setSwaps((s) => [...s, ...moves.map((m) => ({ ...m, id }))]);
      // A hide closes its lines up on the page at once (KAN-584)
      const hiding = hiddenBy(changes);
      if (hiding.length) setHides((h) => [...h, { id, items: hiding }]);
      // A change to an item Tailor changed (a revert included) drops its mark
      // now, not after a compile; a change the render refuses puts it back
      const waiting = latestReview.current;
      const kept =
        waiting &&
        (revertedTarget
          ? reverted(waiting.edits, revertedTarget, held.current.choices)
          : untouched(waiting.edits, changes));
      const unmarked = waiting?.edits.filter((edit) => !kept?.includes(edit)) ?? [];
      if (waiting && kept) {
        latestReview.current = { ...waiting, edits: kept };
        setReview(latestReview.current);
      }
      // The save goes now, beside the render; a refusal is the render's to
      // show, and any other failure puts the saved resume back
      sendChoices(changes);
      // A Fit's cycle (`into`, `hold`) never joins another change: its plan
      // reads the page its own PDF prints
      const joins = !into && !hold;
      const job = jobs.current + 1;
      if (joins) choiceJobs.current.add(job);
      return enqueue(async () => {
        choiceJobs.current.delete(job);
        // Skipped: the change stays on its way (`unanswered`, its swap and
        // its lines), so the next change's copy holds it, and that render
        // answers it. Its step keeps no PDF on either side: Undo and Redo
        // render it (`travel`)
        if (joins && choiceJobs.current.has(job + 1)) {
          if (step) {
            step.before = settled();
            step.pdfBefore = skippedChoice.current ? null : lastPdf.current;
          }
          carried.current.push({ id, changes, lines, step });
          skippedChoice.current = true;
          return;
        }
        const along = carried.current;
        carried.current = [];
        const current = begin();
        started.current = performance.now();
        if (step && !into) {
          step.before = settled();
          step.pdfBefore = skippedChoice.current ? null : lastPdf.current;
        }
        skippedChoice.current = false;
        const sending = along.reduce<ChoicesUpdate>(
          (all, c) => joined({ changes: all }, c.changes),
          {},
        );
        const { data, error, status } = await renderEdit(
          resumeId,
          { changes: along.length ? joined({ changes: sending }, changes) : changes },
          copy(),
        );
        for (const c of [...along, { id, lines }]) {
          unanswered.current.delete(c.id);
          answered(c.id);
          c.lines.forEach(answered);
        }
        // A render that failed twice for any other reason (a timeout, a
        // compile) says nothing of the save beside it. Nor does a refusal
        // of changes carried together: which one was refused, the saves
        // beside them know, so the saved resume comes back
        if (!data && (!refused(status) || along.length)) reload(lostChange(error, "shown"));
        // Refused: the change and its swap leave the page
        keepChoices(data?.choices ?? confirmed.current);
        // A carried step's after was never a page of its own (its after is
        // null, so Redo renders it); refused, it has nothing to undo
        for (const c of along) if (!data && c.step) forget(c.step);
        if (!data) {
          const gone = new Set([id, ...along.map((c) => c.id)]);
          setSwaps((s) => s.filter((x) => !gone.has(x.id)));
          setHides((h) => h.filter((x) => !gone.has(x.id)));
          lines.forEach(drop);
          along.forEach((c) => c.lines.forEach(drop));
          // The record is gone once its last change was: `waiting` still has it
          const now = latestReview.current ?? waiting;
          if (now && unmarked.length) {
            latestReview.current = { ...now, edits: [...now.edits, ...unmarked] };
            setReview(latestReview.current);
          }
        }
        if (data) {
          lastPdf.current = data.render;
          if (step) {
            step.after = settled();
            step.pdfAfter = data.render;
          }
        } else if (step && !into) forget(step);
        if (!current()) return;
        setSaving(false);
        if (!data) return setError(error);
        // A held PDF still gives the next copy the header it printed
        if (hold?.(data.render)) {
          if (data.render.identity) held.current.printed = printedBy(data.render);
        } else keepRendered(data.render);
      });
    },
    [
      begin,
      copy,
      drop,
      enqueue,
      forget,
      keepChoices,
      keepRendered,
      record,
      reload,
      resumeId,
      sendChoices,
      setReview,
      settled,
    ],
  );

  /** One typed line (KAN-391): the save and the render go side by side.
   *  The render answers what the line changed in the copy, read by the API
   *  (a GPA's number, a link's https://); the save answers a bullet's
   *  variant id and the profile after a header field. */
  const saveText = useCallback(
    (item_id: string, kind: string, text: string, recorded = true) => {
      const key = `${item_id}.${kind}`;
      sent(key);
      lastSent.current.set(key, text);
      const step = recorded ? record({ line: { item_id, kind, text } }) : null;
      sendLine({ item_id, kind, text }, copy());
      return enqueue(async () => {
        const current = begin();
        started.current = performance.now();
        if (step) {
          // Read once every edit before it has answered: the line's wording,
          // stored link or printed text as it stands now
          const before = settled();
          step.undo = reverseLine(
            before.bank,
            before.choices,
            { item_id, kind },
            lastPdf.current?.boxes.find((b) => boxKey(b) === key)?.text,
            // A header field's stored value: a link prints without its
            // "https://", and a field the resume hides prints nothing
            item_id === HEADER ? (headerNow.current[kind as HeaderField] ?? null) : undefined,
          );
          step.before = before;
          step.pdfBefore = lastPdf.current;
        }
        const { data, error, status } = await renderEdit(
          resumeId,
          { line: { item_id, kind, text } },
          copy(),
        );
        answered(key);
        if (!data && !refused(status)) reload(lostChange(error, "shown"));
        // Refused: the page shows what is saved, unless the student is
        // still on the line to fix it
        if (!data && key !== selectedNow.current) drop(key);
        // What the line changed is kept even when a newer request owns the
        // page: the next request's copy needs it
        const entry = data?.entry;
        if (entry) {
          held.current.bank = {
            ...held.current.bank,
            entries: held.current.bank.entries.map((e) =>
              e.id === entry.id ? { ...entry, bullets: e.bullets, resume_ids: e.resume_ids } : e,
            ),
          };
          setBank(held.current.bank);
        }
        if (data?.choices) keepChoices(data.choices);
        if (data) {
          lastPdf.current = data.render;
          if (step) {
            step.after = settled();
            step.pdfAfter = data.render;
          }
        } else if (step) forget(step);
        if (!current()) return;
        setSaving(false);
        if (!data) return setError(error);
        if (data.choices) {
          // A typed bullet Tailor changed drops its mark
          const waiting = latestReview.current;
          const changes = { bullets: [{ bullet_id: item_id, text }] };
          if (waiting) setReview({ ...waiting, edits: untouched(waiting.edits, changes) });
        }
        keepRendered(data.render);
      });
    },
    [
      begin,
      copy,
      drop,
      enqueue,
      forget,
      keepChoices,
      keepRendered,
      record,
      reload,
      resumeId,
      sendLine,
      setReview,
      settled,
    ],
  );

  /** A header field typed in the Header panel (KAN-436): a line of the
   *  header, saved and rendered as one typed on the page, so it has Undo. */
  const saveHeader = useCallback(
    (field: HeaderField, text: string) => void saveText(HEADER, field, text),
    [saveText],
  );

  /** Saves typed text when it differs from what the line prints, or, while
   *  its PDF is on its way, from what was last sent for it: the page still
   *  prints the text before, so a line reopened and typed back to it sent
   *  nothing and the sent text came back. Left as it was, it sends nothing
   *  again. */
  const save = useCallback(
    async (typed: Draft) => {
      const shown = rendered?.boxes.find((b) => boxKey(b) === typed.key)?.text;
      const text = typed.text.trim();
      const onItsWay = onTheirWay.current.has(typed.key)
        ? lastSent.current.get(typed.key)
        : undefined;
      if (shown === undefined || text === (onItsWay ?? shown)) return;
      const { item_id, kind } = splitKey(typed.key);
      await saveText(item_id, kind, text);
    },
    [rendered, saveText],
  );

  /** Sends the line's typed text, as the student leaves it (a click away,
   *  Enter, Escape, another line). Nothing goes while they type: a pause
   *  saved half a line once, and the line again when it was done (KAN-391). */
  const flush = useCallback(() => {
    const waiting = pending.current;
    pending.current = null;
    if (waiting) void save(waiting);
  }, [save]);

  const select = useCallback(
    (key: string | null) => {
      // No line opens while a fit runs: its edit would change the page
      // under the plan (`fitting`)
      if (key !== null && fitting.current) return;
      const left = selectedNow.current;
      flush();
      // A line left unchanged has nothing on its way to wait for
      if (left && left !== key && !onTheirWay.current.has(left)) drop(left);
      placed.current = null;
      selectedNow.current = key;
      setSelected(key);
      if (key !== null) setPicked(null);
      if (key === null) refresh();
    },
    [drop, flush, refresh],
  );

  /** The toolbar's switch: the panel, the original, or nothing beside the
   *  page. A hidden panel leaves no line highlighted for a card out of
   *  sight. */
  const showSide = (to: Side) => {
    if (side === "suggestions" && to !== "suggestions") {
      setActive(null);
      setFocused(null);
    }
    // The comparison only reads (`comparing`): an open line saves and closes
    if (to === "original") select(null);
    setSide(to);
  };

  // Esc climbs, as the breadcrumb reads (KAN-920): an open line to its
  // entry, an entry to its section, a section to nothing. It closed the
  // line and nothing more until then. Option with an arrow moves the picked
  // block, or the open line while its field does not have the focus (in a
  // field it moves the caret by a paragraph). Each render hands over its own
  // (`keys`), since they read the line and the outline as drawn
  const keys = useRef<{ climb: () => void; nudge: (by: -1 | 1) => boolean }>({
    climb: () => select(null),
    nudge: () => false,
  });
  useEffect(() => {
    const press = (event: KeyboardEvent) => {
      if (event.key === "Escape") return keys.current.climb();
      if (!event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
      if ((event.target as Element).closest?.("input, textarea, [contenteditable='true']")) return;
      if (keys.current.nudge(event.key === "ArrowUp" ? -1 : 1)) event.preventDefault();
    };
    window.addEventListener("keydown", press);
    return () => window.removeEventListener("keydown", press);
  }, []);

  /** The page as a step left it: its state and its PDF, at once. */
  const restore = useCallback(
    (state: Held, pdf: RenderedPdf) => {
      begin();
      setSaving(false);
      unanswered.current.clear();
      onTheirWay.current.clear();
      held.current = { ...state };
      setBank(state.bank);
      keepChoices(state.choices);
      setSwaps([]);
      setHides([]);
      setDrafts({});
      lastPdf.current = pdf;
      keepRendered(pdf);
      keepPage(pdf.page_settings);
    },
    [begin, keepChoices, keepPage, keepRendered],
  );

  /**
   * Undo (`back`) or Redo (./history.ts). It waits for every render before
   * it, so the step's state is whole. When the step kept the state and PDF
   * on its other side, the page goes back to them at once and only the
   * save goes, with a copy of what the database holds, which the save
   * checks a typed entry field against. Otherwise the edit goes as any
   * other, its line drawn over the page until its PDF lands. An open line
   * is saved first, so Undo then takes back what was just typed.
   */
  const travel = useCallback(
    (back: boolean) => {
      // Cmd+Z too: not between a fit's cycles (`fitting`)
      if (fitting.current) return;
      select(null);
      void enqueue(async () => {
        const from = back ? undos : redos;
        const step = from.current.pop();
        if (!step) return countSteps();
        (back ? redos : undos).current.push(step);
        countSteps();
        const edit = back ? step.undo : step.redo;
        const state = back ? step.before : step.after;
        const pdf = back ? step.pdfBefore : step.pdfAfter;
        const saved = back ? step.after : step.before;
        if (!edit) return;
        if ("name" in edit) return applyName.current?.(edit.name, () => forget(step));
        // Not past a page's render still queued (a skipped step's Undo sends
        // one): it would land after this and print its settings over them
        if (state && pdf && saved?.printed && pageJobs.current.size === 0) {
          restore(state, pdf);
          const source = {
            entries: saved.bank.entries,
            skills: saved.bank.skills,
            sections: saved.bank.sections,
            choices: saved.choices,
            ...saved.printed,
            page_settings: pdf.page_settings,
          };
          if ("changes" in edit) sendChoices(edit.changes);
          else if ("page" in edit) sendPage(edit.page);
          else sendLine(edit.line, source);
          return;
        }
        if ("changes" in edit) {
          void apply(edit.changes, undefined, false);
        } else if ("page" in edit) {
          void applyPage(edit.page, false);
        } else {
          const { item_id, kind, text } = edit.line;
          if (!(LINK_FIELDS as readonly string[]).includes(kind))
            setDrafts((d) => ({ ...d, [`${item_id}.${kind}`]: text }));
          void saveText(item_id, kind, text, false);
        }
      });
    },
    [
      apply,
      applyPage,
      countSteps,
      enqueue,
      forget,
      restore,
      saveText,
      select,
      sendChoices,
      sendLine,
      sendPage,
    ],
  );

  // Cmd+Z (Ctrl+Z) undoes, Shift+Cmd+Z or Ctrl+Y redoes; inside a field the
  // field's own text undo runs instead
  useEffect(() => {
    if (phone) return;
    const keys = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey) return;
      if ((event.target as Element).closest?.("input, textarea, [contenteditable='true']")) return;
      const key = event.key.toLowerCase();
      if (key !== "z" && key !== "y") return;
      event.preventDefault();
      travel(key === "z" && !event.shiftKey);
    };
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [phone, travel]);

  // On a desktop, a press outside the page, the bar and the assistant (each
  // marked KEEPS_SELECTION) saves the line and clears the selection. The
  // assistant keeps it: it acts on the selected line. The phone editor
  // covers the screen and closes its own sheet.
  useEffect(() => {
    if (!selected || phone) return;
    const away = (event: PointerEvent) => {
      if (!(event.target as Element).closest?.(`[${KEEPS_SELECTION}]`)) select(null);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [selected, phone, select]);
  // A picked block lets go the same way (KAN-920): a press off the page and
  // the bar. A press on a line opens it instead (`select`)
  useEffect(() => {
    if (!picked || phone) return;
    const away = (event: PointerEvent) => {
      if (!(event.target as Element).closest?.(`[${KEEPS_SELECTION}], [data-box]`)) setPicked(null);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [picked, phone]);

  function type(key: string, text: string) {
    setDrafts((d) => ({ ...d, [key]: text }));
    pending.current = { key, text };
  }

  /**
   * Fit to One Page from the page on screen (KAN-584): the copy and the PDF
   * it printed go to `POST .../fit/plan`, which compiles nothing and answers
   * the cuts that fit by prediction; they are an edit like any other, so the
   * page closes them up at once and the render and the save go behind it.
   * While the new PDF is still over one page, the next cycle plans from it.
   * The whole fit, every cycle, is one Undo step. An API a deploy behind sends no measure,
   * and then the server fits (`fitOnServer`).
   */
  async function fit() {
    if (fitting.current) return;
    fitting.current = true;
    setFittingNow(true);
    try {
      await fitHere();
    } finally {
      fitting.current = false;
      setFittingNow(false);
    }
  }

  async function fitHere() {
    select(null);
    // The copy and the PDF it printed, once every render before has landed
    const start = await enqueue(async () => ({ pdf: lastPdf.current, source: copy() }));
    const first = start.pdf && measureOf(start.pdf);
    if (!start.pdf || !start.source || !first) return fitOnServer();
    // A page setting whose compile was skipped has no PDF of its own
    if (!samePage(start.pdf.page_settings, start.source.page_settings)) return fitOnServer();
    if (start.pdf.page_count <= 1) return;
    const source = start.source;
    let now: RenderMeasure | null = null;
    let taken = 0;
    let step: Step<Held, RenderedPdf> | undefined;
    // Only the final PDF paints: a cycle's PDF still over one page is held,
    // and the page keeps its cuts closed up while the next cycle plans from
    // it, so a fit off by a line shows one render, not two. A fit that ends
    // on a held PDF (nothing left to cut, a failed plan) paints it then.
    let unpainted: RenderedPdf | null = null;
    const over = (pdf: RenderedPdf) => pdf.page_count > 1;
    try {
      for (;;) {
        const { data, error } = await planFitHere(resumeId, { source, first, now, taken });
        if (!data) return setError(error);
        if (!changesAny(data.hide)) return;
        taken = data.taken;
        const before = lastPdf.current;
        const applied = apply(data.hide, undefined, !step, {}, step, over);
        step ??= undos.current.at(-1);
        await applied;
        const after = lastPdf.current;
        // Refused or failed: `apply` put the page back and said why
        if (!after || after === before) return;
        cutsNow.current = addCuts(cutsNow.current, data.undo);
        setCuts(cutsNow.current);
        keepFitCuts(resumeId, cutsNow.current);
        if (!over(after)) return;
        unpainted = after;
        now = measureOf(after);
        if (!now) return;
      }
    } finally {
      // Not when a newer PDF has landed since (a reload, the final cycle)
      if (unpainted && lastPdf.current === unpainted) keepRendered(unpainted);
    }
  }

  /** Fit to One Page on the server, for an API that sends no measure: it
   *  reads the saved resume, compiles it and cuts until a render fits. */
  function fitOnServer() {
    return enqueue(async () => {
      // Fit reads the saved resume, so every save sent before goes first
      await saves.current;
      const current = begin();
      started.current = performance.now();
      const before = settled();
      const pdfBefore = lastPdf.current;
      markResumesStale();
      const { data, error } = await fitToOnePage(resumeId);
      if (!current()) return;
      if (!data) {
        setSaving(false);
        return setError(error);
      }
      announce(false);
      lastPdf.current = data.render;
      keepRendered(data.render);
      const hid =
        data.undo.bullets?.length || data.undo.entries?.length || data.undo.skills?.length;
      if (hid) {
        cutsNow.current = addCuts(cutsNow.current, data.undo);
        setCuts(cutsNow.current);
        keepFitCuts(resumeId, cutsNow.current);
      }
      const fresh = await getChoices(resumeId);
      if (fresh.data) keepChoices(fresh.data);
      // Fit is one step like any edit: Undo (the button or Cmd+Z) shows what
      // it hid, Redo hides it again. It had an Undo Fit button of its own
      // until 2026-11-01, a second way to do what Undo does.
      if (hid && fresh.data) {
        push(undos.current, {
          undo: { changes: data.undo },
          redo: { changes: hideAgain(data.undo) },
          before,
          after: settled(),
          pdfBefore,
          pdfAfter: data.render,
        });
        redos.current = [];
        countSteps();
      }
      if (current()) setSaving(false);
    });
  }

  const box = rendered?.boxes.find((b) => boxKey(b) === selected);
  const line = box ? lineOf(bank, box) : null;
  // The live page (KAN-391): while a wrapping line's typed text differs from
  // what the PDF prints, the page under it moves by the lines it gained or
  // lost. When the next PDF lands with that text, the shift is 0 again;
  // where TeX wraps the same text otherwise, the page jumps then.
  const overlaid = [
    ...(line && typed(line) && selected ? [selected] : []),
    ...Object.keys(drafts).filter((k) => k !== selected),
  ];
  // What the page under an overlaid line moves by, against the box of the
  // PDF on screen: the lines its typed text gained or lost, 0 once that PDF
  // prints the text
  const shiftOf = (target: RenderBox) => {
    const text = drafts[boxKey(target)];
    const lines = draftLines[boxKey(target)];
    if (text === undefined || !lines || !WRAPS.has(target.kind) || text.trim() === target.text) {
      return 0;
    }
    const step = rendered?.wrapped_line ?? DEFAULT_WRAPPED_LINE;
    return (lines - boxLines(target, step)) * step;
  };

  // The moves on their way as strips of the page on screen, each against
  // the page after the ones before: a bullet is its box, an entry its
  // fields' and bullets' boxes. A swap the page already shows (`a` no
  // longer above `b`), or one across a page break, is left out.
  const swapsOn = (boxes: RenderBox[]) => {
    const strips: Strip[] = [];
    let placed = boxes;
    const regionOf = (kind: Swap["kind"], id: string) => {
      // A section is its heading and everything under it (KAN-920)
      if (kind === "section") return sectionStrip(placed, bank, id);
      const bullets = new Set(
        kind === "entry" ? bank.entries.find((e) => e.id === id)?.bullets.map((b) => b.id) : [],
      );
      const own = placed.filter((b) =>
        kind === "bullet"
          ? b.kind === "bullet" && b.item_id === id
          : (b.item_id === id && b.kind !== "bullet") ||
            (b.kind === "bullet" && bullets.has(b.item_id)),
      );
      if (!own.length || own.some((b) => b.page !== own[0].page)) return null;
      if (kind === "bullet" && own.length !== 1) return null;
      return {
        page: own[0].page,
        top: Math.min(...own.map((b) => b.y0)),
        bottom: Math.max(...own.map((b) => b.y1)),
      };
    };
    for (const swap of swaps) {
      const a = regionOf(swap.kind, swap.a);
      const b = regionOf(swap.kind, swap.b);
      if (!a || !b || a.page !== b.page || a.bottom > b.top) continue;
      const strip: Strip = { page: a.page, a: [a.top, a.bottom], b: [b.top, b.bottom] };
      strips.push(strip);
      placed = placed.map((x) => afterStrips(x, [strip]));
    }
    return strips;
  };

  // The hides on their way as bands of the page that close up (KAN-584): an
  // entry is its fields' and bullets' boxes, a bullet its box, each with the
  // space under it when the next line is close (`GAP_SPACE`), so the lines
  // below rise to where the hidden ones began. A larger space is a section
  // heading's, which stays. A skill leaves its line instead (`skillCut`);
  // an item the page no longer prints draws nothing.
  const gapsOn = (boxes: RenderBox[]): Gap[] => {
    if (!hides.length) return [];
    const gone = new Set(hides.flatMap((h) => h.items));
    for (const entry of bank.entries)
      if (gone.has(entry.id)) for (const b of entry.bullets) gone.add(b.id);
    const line = rendered?.wrapped_line ?? DEFAULT_WRAPPED_LINE;
    const skills = boxes
      .filter((box) => box.kind === "skill" && gone.has(box.item_id))
      .flatMap((box) => skillCut(box, boxes, gone, line));
    const bands = boxes
      .filter((box) => box.kind !== "skill" && gone.has(box.item_id))
      .map((box) => {
        const next = Math.min(
          ...boxes.filter((o) => o.page === box.page && o.y0 >= box.y1 - 0.5).map((o) => o.y0),
        );
        const space = next - box.y1;
        return { page: box.page, top: box.y0, bottom: box.y1 + (space <= GAP_SPACE ? space : 0) };
      });
    return [...bands, ...skills];
  };

  // Bullets typed in on the page (KAN-920): each opens a line under the
  // bullet it follows, where the PDF will print it. The space between two
  // bullets of one entry, read from the page, sets where its text sits.
  const entryOfBullet = useMemo(() => {
    const of = new Map<string, string>();
    for (const e of bank.entries) for (const b of e.bullets) of.set(b.id, e.id);
    return of;
  }, [bank]);
  // On `page`: LaTeX stretches the space per page to fill it (2.94pt on
  // one page of the test resume, 2.65pt on another), so the least on any
  // page opened a line short, and its dot sat high
  const bulletSpace = (boxes: RenderBox[], page: number) => {
    const bullets = boxes
      .filter((b) => b.kind === "bullet" && b.page === page)
      .sort((a, b) => a.y0 - b.y0);
    const gaps: number[] = [];
    for (let i = 1; i < bullets.length; i++) {
      const [a, b] = [bullets[i - 1], bullets[i]];
      const gap = b.y0 - a.y1;
      if (entryOfBullet.get(a.item_id) === entryOfBullet.get(b.item_id))
        if (gap > 0 && gap < GAP_SPACE) gaps.push(gap);
    }
    // The middle one: every gap on a page is the same but for rounding
    gaps.sort((a, b) => a - b);
    return gaps.length ? gaps[Math.floor(gaps.length / 2)] : 2.9;
  };
  /** A new bullet's place against these boxes: under its anchor's last
   *  line, `space` below it, one line tall (`one`) and as many more as its
   *  text wraps to. */
  const newPlace = (n: NewBullet, boxes: RenderBox[]) => {
    const own = boxes.filter((b) => b.kind === "bullet" && b.item_id === n.anchor);
    if (!own.length) return null;
    const last = own.reduce((a, b) =>
      b.page > a.page || (b.page === a.page && b.y1 > a.y1) ? b : a,
    );
    const step = rendered?.wrapped_line ?? DEFAULT_WRAPPED_LINE;
    const one = last.y1 - last.y0 - (boxLines(last, step) - 1) * step;
    const space = bulletSpace(boxes, last.page);
    return { last, one, space, lines: draftLines[`${n.key}.bullet`] ?? 1, step };
  };
  const insertsOn = (boxes: RenderBox[]) => {
    const printed = new Set(boxes.map((b) => b.item_id));
    return placeNew(newBullets, (key) => {
      const id = newIds.current.get(key);
      return id && printed.has(id) ? id : undefined;
    }).flatMap((n) => {
      const at = newPlace(n, boxes);
      if (!at) return [];
      const y = at.last.y1 + at.space / 2;
      return [
        {
          ...at.last,
          item_id: n.key,
          text: "",
          y0: y,
          y1: y,
          by: at.space + at.one + (at.lines - 1) * at.step,
        },
      ];
    });
  };

  /** Opens a new bullet's line under `after` (KAN-920): a printed bullet,
   *  or a new one still on its way, whose line it is drawn under. */
  const openNew = (entryId: string, after: string) => {
    select(null);
    setPicked(null);
    const key = `new-bullet-${++newCount.current}`;
    setNew((list) => {
      const before = list.findIndex((n) => n.key === after);
      const item: NewBullet = {
        key,
        entryId,
        anchor: before >= 0 ? list[before].anchor : after,
        after,
        text: "",
        saving: false,
      };
      return before < 0
        ? [...list, item]
        : [...list.slice(0, before + 1), item, ...list.slice(before + 1)];
    });
  };
  const dropNew = (key: string) => setNew((list) => list.filter((n) => n.key !== key));

  /** Leaves a new bullet's line: an empty one goes; one with text is added
   *  to its entry, then shown on this resume after the bullet it follows, as
   *  one change with Undo. `next` opens another line under it (Enter). */
  const leaveNew = (key: string, next = false) => {
    const n = newNow.current.find((x) => x.key === key);
    if (!n || n.saving) return;
    const text = n.text.trim();
    if (!text) return dropNew(key);
    setNew((list) => list.map((x) => (x.key === key ? { ...x, text, saving: true } : x)));
    if (next) openNew(n.entryId, key);
    adding.current = adding.current.then(async () => {
      const { data, error } = await addBullet(n.entryId, text);
      if (!data) {
        dropNew(key);
        setError(error ?? "Your bullet didn't save. Try again.");
        return;
      }
      newIds.current.set(key, data.id);
      const bank = held.current.bank;
      held.current.bank = {
        ...bank,
        entries: bank.entries.map((e) =>
          e.id === n.entryId ? { ...e, bullets: [...e.bullets, data] } : e,
        ),
      };
      setBank(held.current.bank);
      // It follows a printed bullet, or a new one: that one's id, or, if it
      // did not save, the bullet that one followed
      let after = n.after;
      while (after.startsWith("new-bullet-")) {
        const id = newIds.current.get(after);
        if (id) {
          after = id;
          break;
        }
        after = newNow.current.find((x) => x.key === after)?.after ?? n.anchor;
      }
      announce(true);
      await apply({
        bullets: bulletsWithNew(held.current.bank, held.current.choices, n.entryId, data.id, after),
      });
    });
  };

  /** A new bullet's line: its field while typed in, its text once left,
   *  with the dot the PDF will print beside it. */
  function newField(n: NewBullet, target: RenderBox) {
    const key = `${n.key}.bullet`;
    const at = newPlace(n, rendered?.boxes ?? []);
    const look = lineLook({ ...target, item_id: n.anchor });
    const half = (at?.space ?? 2) / 2;
    // The PDF's own dot, where Jake's puts it (`DOT_LEFT`, `DOT_DOWN`,
    // `DOT_SIZE`): a guess, then a coarse measure, sat off the dots above
    // An SVG circle in a box three times its width, never a rounded box:
    // Chrome snaps a box's painted edges to whole pixels, and at about 3.4px
    // across a `rounded-full` box rounded to 3 by 4 and drew an oval (the
    // user saw it stretched). The circle keeps its shape in any box
    const dot = (
      <svg
        aria-hidden
        viewBox="0 0 30 30"
        className="absolute"
        style={{
          width: pt(DOT_SIZE * 3),
          height: pt(DOT_SIZE * 3),
          left: `-${pt(DOT_LEFT + (DOT_SIZE * 3) / 2)}`,
          top: pt(half + DOT_DOWN - (DOT_SIZE * 3) / 2),
        }}
      >
        <circle cx="15" cy="15" r="5" fill="#000" />
      </svg>
    );
    if (n.saving)
      return (
        <div
          ref={(element) => measure(key, "bullet", element)}
          className="relative"
          style={{ paddingTop: pt(half) }}
        >
          {dot}
          <div
            aria-hidden
            className={cn(look.className, "break-words whitespace-pre-wrap")}
            style={look.style}
          >
            {wordsOf(n.text)}
          </div>
        </div>
      );
    return (
      <div className="relative" style={{ paddingTop: pt(half) }}>
        {dot}
        {richLine(
          n.text,
          (text) => setNew((list) => list.map((x) => (x.key === n.key ? { ...x, text } : x))),
          {
            attach: (element) => {
              if (element && !focusedNew.current.has(n.key)) {
                focusedNew.current.add(n.key);
                element.focus({ preventScroll: true });
              }
              return measure(key, "bullet", element);
            },
            "aria-label": "New bullet",
            onBlur: () => leaveNew(n.key),
            // Enter adds it and opens the next line; Escape leaves it (an
            // empty line goes), never climbing out of a block as it does
            onKeyDown: (e) => {
              if (e.key !== "Enter" && e.key !== "Escape") return;
              e.preventDefault();
              e.stopPropagation();
              leaveNew(n.key, e.key === "Enter");
            },
            // The field any line is typed in (its ring), on the dot and in
            // the type and ink the PDF will print, with no grey hint: a "New
            // bullet" hint looked like no line on the page (2026-11-19)
            className: cn(look.className, FIELD_RING),
            style: look.style,
          },
        )}
      </div>
    );
  }

  /** The text a typed line's field opens on: what the line prints. */
  function startText(line: Line, target: RenderBox) {
    return typed(line) ? target.text : null;
  }

  /** Keeps `draftLines` current for a wrapping line's field or text: it
   *  grows with its text, so its height says how many lines it wraps to. */
  function measure(key: string, kind: string, element: HTMLElement | null) {
    if (!element || !WRAPS.has(kind)) return;
    const observer = new ResizeObserver(() => {
      const height = parseFloat(getComputedStyle(element).lineHeight);
      const lines = Math.round(element.offsetHeight / height);
      if (height > 0) setDraftLines((d) => (d[key] === lines ? d : { ...d, [key]: lines }));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }

  /** Jake's type for a box's line, as the field and the read-only text set it. */
  function lineLook(target: RenderBox) {
    const of = lineOf(bank, target);
    const settings = rendered?.page_settings ?? DEFAULT_PAGE;
    const entry = of?.kind === "entry" || of?.kind === "bullet" ? of.entry : null;
    const look = typeOf(
      target.kind,
      entry?.section ?? null,
      settings,
      entry ? degreeLeads(entry, settings) : false,
      entry ? companyLeads(entry, settings) : false,
    );
    const wraps = WRAPS.has(target.kind);
    // A wrapping line's field steps as the page's lines do
    const lineHeight = wraps
      ? (rendered?.wrapped_line ?? DEFAULT_WRAPPED_LINE) / look.size
      : LINE_HEIGHT;
    return {
      className: cn(
        latinModern.className,
        // A negative margin puts the side padding outside the text, so the
        // text lands on the PDF's own glyphs
        // The page's own ink, pure black on white paper in either theme:
        // the app's near-black `text-ink` set typed text a shade off the
        // printed lines around it
        "-mx-[0.4cqw] block bg-white px-[0.4cqw] text-black",
        look.bold && "font-bold",
        look.italic && "italic",
      ),
      style: {
        fontFamily: FONTS.find((font) => font.value === settings.font_family)?.css,
        fontSize: pt(look.size),
        lineHeight: pt(look.size * lineHeight),
        // Puts the text's baseline on the PDF's
        marginTop: pt(boxAscent(target.kind) - fieldBaseline(lineHeight) * look.size),
        ...(wraps
          ? {
              width: `calc(${pt(PAGE_WIDTH - settings.side_margin * 72 - target.x0)} + 0.8cqw)`,
              textAlign: settings.alignment === "justified" ? ("justify" as const) : undefined,
            }
          : { minWidth: pt(40) }),
      },
    };
  }

  /** What the page draws over an overlaid line: the selected line's field,
   *  or a line's typed text while the PDF that prints it is on its way. */
  function overlay(target: RenderBox) {
    const fresh = newBullets.find((n) => n.key === target.item_id);
    if (fresh) return newField(fresh, target);
    const key = boxKey(target);
    if (key === selected) return field(target);
    const text = drafts[key];
    if (text === undefined) return null;
    const look = lineLook(target);
    // A click on the text reopens the line with what was typed, while its
    // PDF is still on its way: the text sits over the line's own target,
    // and the press closed the line instead (`data-box` keeps it a line's)
    return (
      <div
        ref={(element) => measure(key, target.kind, element)}
        aria-hidden
        data-box={key}
        onClick={() => onLine(key)}
        className={cn(look.className, "cursor-text break-words whitespace-pre-wrap")}
        style={look.style}
      >
        {target.kind === "bullet" ? wordsOf(text) : text}
      </div>
    );
  }

  function wordsOf(text: string) {
    return runs(text).map((run, i) => (
      <span key={i} className={cn(run.bold && "font-bold", run.italic && "italic")}>
        {run.text}
      </span>
    ));
  }

  /** A rich field, so bold and italic show in the words as they are set
   *  (KAN-435): a textarea showed their markers until the line was left. React
   *  holds no children here; `showMarked` keeps it to `value`, so a change from
   *  elsewhere (Undo on its suggestion) still reaches it. Ctrl or Cmd+B and I
   *  set bold and italic here, since the bar's Bold and Italic went (KAN-586):
   *  a browser's own shortcut is not certain in a contentEditable, and one
   *  sent by a script (the Browser pane's) never ran. The browser gives it
   *  text undo. */
  function richLine(
    value: string,
    onText: (text: string) => void,
    {
      attach,
      className,
      onKeyDown,
      ...rest
    }: Omit<ComponentProps<"div">, "ref" | "onInput" | "onPaste" | "onDrop"> & {
      attach: (element: LineField | null) => (() => void) | undefined;
    },
  ) {
    return (
      <div
        {...rest}
        // Its own element: its words are the browser's, so a plain div drawn in
        // its place by React (the line's words on their way) would keep them
        // and add its own beside them
        key="rich-line"
        ref={(element) => {
          if (element) showMarked(element, value);
          return attach(element);
        }}
        role="textbox"
        aria-multiline
        contentEditable
        suppressContentEditableWarning
        className={cn(className, "min-h-lh break-words whitespace-pre-wrap")}
        onInput={(e) => onText(readMarked(e.currentTarget))}
        onKeyDown={(e) => {
          const mark = { b: "bold", i: "italic" }[e.key.toLowerCase()];
          if (mark && (e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey) {
            e.preventDefault();
            // Fires an input event, which `onInput` above reads
            document.execCommand(mark);
            return;
          }
          onKeyDown?.(e);
        }}
        // Plain words on one line only: a paste would bring its own fonts
        onPaste={(e) => {
          e.preventDefault();
          const words = e.clipboardData.getData("text/plain").replace(/\s+/g, " ");
          document.execCommand("insertText", false, words);
        }}
        onDrop={(e) => e.preventDefault()}
      />
    );
  }

  /** Focuses a field once per selection, with the caret where the press
   *  landed on the PDF (the field's text sits over the same glyphs), or at
   *  the end. */
  function focusAt(key: string, element: LineField | null) {
    if (!element || placed.current === key) return;
    placed.current = key;
    element.focus({ preventScroll: true });
    const at = pressed.current;
    const origin = pages.current?.getBoundingClientRect();
    const caret =
      at && origin && document.caretPositionFromPoint?.(origin.left + at.x, origin.top + at.y);
    if (element instanceof HTMLDivElement) {
      const range = document.createRange();
      range.selectNodeContents(element);
      range.collapse(false);
      if (caret && element.contains(caret.offsetNode)) {
        range.setStart(caret.offsetNode, caret.offset);
        range.collapse(true);
      }
      getSelection()?.removeAllRanges();
      getSelection()?.addRange(range);
      return;
    }
    const offset = caret && caret.offsetNode === element ? caret.offset : element.value.length;
    element.setSelectionRange(offset, offset);
  }

  function field(target: RenderBox) {
    const start = line && startText(line, target);
    if (start == null || !line) return null;
    const key = boxKey(target);
    const look = lineLook(target);
    const value = drafts[key] ?? start;
    const attach = (element: LineField | null) => {
      focusAt(key, element);
      return measure(key, target.kind, element);
    };
    const common = {
      "aria-label": kindLabel(target.kind),
      onBlur: () => flush(),
      // Enter saves the line and clears the selection, back to the page
      onKeyDown: (e: React.KeyboardEvent) => {
        if (e.key !== "Enter") return;
        e.preventDefault();
        select(null);
      },
      className: cn(look.className, FIELD_RING),
      style: look.style,
    };
    if (target.kind === "bullet") {
      return richLine(value, (text) => type(key, text), { ...common, attach });
    }
    const text = {
      ...common,
      ref: attach,
      value,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        type(key, e.target.value),
    };
    return WRAPS.has(target.kind) ? <textarea {...text} rows={1} /> : <input {...text} />;
  }

  /** Called when every page of a new PDF has painted: a line whose save
   *  has landed is now printed by the page itself, so its typed text goes. */
  const drawn = () => {
    // A new bullet the PDF now prints goes, and the next typed after it is
    // drawn under it
    const printed = new Set(rendered?.boxes.map((b) => b.item_id));
    const placed = placeNew(newNow.current, (key) => {
      const id = newIds.current.get(key);
      return id && printed.has(id) ? id : undefined;
    });
    if (placed.length !== newNow.current.length) setNew(() => placed);
    setDrafts((d) => {
      const kept = Object.entries(d).filter(
        ([k]) => k === selectedNow.current || onTheirWay.current.has(k),
      );
      return kept.length === Object.keys(d).length ? d : Object.fromEntries(kept);
    });
    setSwaps((s) => {
      const kept = s.filter((x) => onTheirWay.current.has(x.id));
      return kept.length === s.length ? s : kept;
    });
    setHides((h) => {
      const kept = h.filter((x) => onTheirWay.current.has(x.id));
      return kept.length === h.length ? h : kept;
    });
    refresh();
    // The edit-to-PDF round trip, from the send to the paint, as a
    // performance measure: the open production check reads it in the
    // browser's developer tools (Safari's on an iPhone). The phone's bar
    // showed it ("Saved, 412 ms") until KAN-799, which was noise to a student
    if (started.current == null) return;
    performance.measure("resume edit round trip", { start: started.current });
    started.current = null;
  };

  const hide = (changes: ChoicesUpdate) => {
    apply(changes);
    select(null);
  };
  const assistant = (className: string) => (
    <Assistant
      resumeId={resumeId}
      bank={bank}
      choices={choices}
      line={line?.kind === "header" ? null : line}
      pageCount={rendered?.page_count ?? 1}
      onApply={apply}
      onHide={hide}
      onFit={fit}
      className={className}
    />
  );

  /** The page area: `draw`n from the PDF in hand, or, until the first
   *  render lands, its skeleton and then FirstRenderPane's error if it
   *  failed. Both layouts draw their pages through it. */
  const pdfPane = (draw: (pdf: RenderedPdf) => ReactNode) =>
    rendered ? (
      draw(rendered)
    ) : (
      <Suspense fallback={<PageSkeleton />}>
        <FirstRenderPane initial={initial} onLoad={adopt} resumeId={resumeId} />
      </Suspense>
    );
  // Tailor's review, on Tailor's page only (`suggestions`)
  const reviewing = suggestions && review ? review : null;
  const cards = reviewing ? cardsOf(reviewing.edits, choices) : undefined;
  // Each line's place on the page, so the panel lists entries as the page does
  const boxOrder = new Map<string, number>();
  rendered?.boxes.forEach((b, i) => {
    if (!boxOrder.has(boxKey(b))) boxOrder.set(boxKey(b), i);
  });
  const pageOrder = (key: string) => boxOrder.get(key) ?? Number.POSITIVE_INFINITY;
  const suggestionCount = reviewing ? reviewing.edits.length : 0;
  // Every changed line is tinted by its change's type; the lines of the card
  // in focus or open also take an outline. A phone tints only those and keeps
  // a dot per line, since a tap there opens a sheet, not a popup
  const allMarks = reviewing ? marksOf(reviewing.edits, choices) : undefined;
  const litEdits = reviewing?.edits.filter((edit) => [focused, active].includes(editKey(edit)));
  const lit = new Set(litEdits?.flatMap((edit) => linesOf(edit, choices)));
  const marks = allMarks && new Map([...allMarks].filter(([line]) => lit.has(line)));
  const dots =
    allMarks &&
    new Map([...allMarks].map(([line, mark]) => [line, { mark, lit: lit.has(line) }] as const));
  // The page scrolls to a suggestion's lines only once it is opened: on
  // hover it scrolled under the pointer as it crossed the panel, which made
  // the page swim. Hover still highlights the lines (`lit`, above)
  const openEdit = reviewing?.edits.find((edit) => editKey(edit) === active);
  const focus = openEdit ? linesOf(openEdit, choices) : undefined;
  // The change on the open line, in a small card beside it, until the
  // student types, closes it or leaves the line. Archived: Tailor's review
  // passes no `suggestionPopup` (POPUP_LIVE in tailor-suggestions.tsx)
  const popupCard =
    showMarks && selected && selected !== closedPopup && drafts[selected] === undefined
      ? cards?.get(selected)
      : undefined;
  const popupEdit = reviewing?.edits.find((edit) => editKey(edit) === popupCard);
  /** A click on a line selects it, and a changed one also opens Suggestions
   *  beside the page, on that line's card (`SuggestionsPanel` scrolls to
   *  it), unless Hide Suggestions has taken the marks off the page. While
   *  the popup was live the panel stayed as it was: the popup said the same
   *  thing, and the panel took the column from a student who had closed it. */
  const onLine = (key: string) => {
    select(selected === key ? null : key);
    const card = cards?.get(key);
    if (!card) return;
    setActive(card);
    setClosedPopup(null);
    if (showMarks) setSide("suggestions");
  };
  /** A click on a margin dot opens its card (on a phone, in the sheet). */
  const onDot = (key: string) => {
    const card = cards?.get(key);
    if (!card) return;
    setActive(card);
    setSuggestionsOpen(true);
  };
  const SuggestionPopup = suggestionPopup;
  const popupNode =
    popupEdit && SuggestionPopup ? (
      <SuggestionPopup
        edit={popupEdit}
        bank={bank}
        choices={choices}
        undo={() => {
          select(null);
          void apply(
            revertOf({ edit: popupEdit }, choices),
            { edit: popupEdit },
            true,
            wordsBack([popupEdit]),
          );
        }}
        close={() => setClosedPopup(selected)}
      />
    ) : undefined;
  const Suggestions = suggestions;
  const panel =
    reviewing && Suggestions ? (
      <Suggestions
        record={reviewing}
        pageOrder={pageOrder}
        bank={bank}
        choices={choices}
        undo={(edit) => void apply(revertOf({ edit }, choices), { edit }, true, wordsBack([edit]))}
        undoAll={() =>
          void apply(
            revertAll(reviewing.edits, choices),
            undefined,
            true,
            wordsBack(reviewing.edits),
          )
        }
        close={() => showSide(null)}
        focused={focused}
        focus={setFocused}
        show={(key) => {
          setActive(key);
          setSuggestionsOpen(false);
        }}
        active={active}
        open={setActive}
        marks={{ shown: showMarks, onToggle: () => setShowMarks(!showMarks) }}
      />
    ) : null;
  // Beside the page, the toolbar's Suggestions shows and hides the panel;
  // the phone opens it as a sheet from its own button
  const shownPanel = side === "suggestions" && panel;
  const shownOriginal = side === "original" && original;
  const shownTabs = tabbed(side);
  const shownCut = side === "cut";
  const cutOpen = suggestions ? shownCut : scoutOpen && panelView === "cut";
  const headerPanel = (
    <HeaderPanel
      header={header}
      email={rendered?.identity?.email ?? null}
      hidden={page.hidden_header}
      onSave={saveHeader}
      onShow={(field, shown) =>
        void applyPage({
          ...page,
          hidden_header: shown
            ? page.hidden_header.filter((f) => f !== field)
            : [...page.hidden_header, field],
        })
      }
    />
  );
  // The Header is the outline's first row (KAN-586): it was a panel of its
  // own beside Sections for a day. Open or closed is the editor's, since a
  // click on the header's line on the page opens it
  const [headerOpen, setHeaderOpen] = useState(false);
  // The outline's entry form (KAN-586): an entry's Edit, or a section's Add.
  // A save writes the bank, so the editor reads it again (`reload`), which
  // also ends the Undo steps before it, as any change from outside does
  const [entryForm, setEntryForm] = useState<{
    target: BankEntry | null;
    section: EntrySection;
    customSectionId: string | null;
    /** A page's + (KAN-920): a new entry goes after this one, or first in
     *  its section when null; a new bullet row opens after this bullet. */
    place?: { after: string | null };
    newBulletAfter?: string;
  } | null>(null);
  const formOpener = useRef<() => HTMLElement | null>(() => null);
  const openEntryForm = (form: NonNullable<typeof entryForm>, opener: HTMLElement) => {
    formOpener.current = () => opener;
    setEntryForm(form);
  };
  /** A section's outline id as the bank names it: a fixed section, or a
   *  custom one by its key (`customKey`). */
  const sectionOf = (id: string): { section: EntrySection; customSectionId: string | null } => {
    if (!id.startsWith("custom:")) return { section: id as EntrySection, customSectionId: null };
    const custom = bank.sections.find((s) => customKey(s.name) === id);
    return { section: "custom", customSectionId: custom?.id ?? null };
  };
  // The walkthrough's hooks into the editor (./walkthrough.tsx)
  const openPanel = (view: PanelTab) => {
    setTab(view);
    setPanelView(view);
    setScoutOpen(true);
  };
  const walkApi: WalkApi = {
    counts: walkCounts(bank, choices, page.section_order, header),
    sampleTicks: sample ? sampleTicked(sample) : null,
    lineOpen: selected !== null,
    pageKey: JSON.stringify(page),
    openSection: (id) => {
      setHeaderOpen(id === "header");
      openPanel("sections");
    },
    openFormat: () => openPanel("format"),
    openExperiences: () => {
      if (!bank.entries.length && !bank.skills.length) setSample((s) => s ?? sampleChoices());
      setPanelView("experiences");
      setScoutOpen(true);
    },
    closeExperiences: () => {
      setSample(null);
      openPanel("sections");
    },
  };
  const sectionsOutline = (
    <>
      <SectionsOutline
        bank={bank}
        choices={choices}
        order={page.section_order}
        onOrder={(section_order) => void applyPage({ ...page, section_order })}
        onApply={apply}
        header={headerPanel}
        lit={walkChapter ? [walkChapter] : []}
        reveal={walkChapter}
        headerOpen={headerOpen}
        onHeaderOpen={setHeaderOpen}
        onEditEntry={(entryId, opener) => {
          const target = bank.entries.find((e) => e.id === entryId);
          if (target)
            openEntryForm(
              {
                target,
                section: target.section,
                customSectionId: target.custom_section_id ?? null,
              },
              opener,
            );
        }}
        onAddEntry={(sectionId, opener) =>
          openEntryForm({ target: null, ...sectionOf(sectionId) }, opener)
        }
        onAddSkill={async (group, name) => {
          // A skill the bank already has (any case) goes on this resume in
          // this group, at its end, with Undo: the API refuses a second copy
          const key = name.trim().toLowerCase();
          const held = bank.skills.find((skill) => skill.name.trim().toLowerCase() === key);
          if (held) {
            if (choices.skills.find((c) => c.skill_id === held.id)?.shown)
              return `${held.name} is already on this resume.`;
            const last = Math.max(-1, ...choices.skills.map((c) => c.position));
            apply({ skills: [{ skill_id: held.id, shown: true, position: last + 1, group }] });
            return null;
          }
          const { error } = await addSkill(name, group || null, resumeId);
          if (error) return error;
          reload(null);
          return null;
        }}
      />
      {entryForm && (
        <OutlineEntryDialog
          bank={bank}
          choices={choices}
          resumeId={resumeId}
          target={entryForm.target}
          section={entryForm.section}
          customSectionId={entryForm.customSectionId}
          returnTo={formOpener}
          tip={walkChapter === entryForm.section ? ENTRY_TIPS[entryForm.section] : undefined}
          newBulletAfter={entryForm.newBulletAfter}
          onClose={() => setEntryForm(null)}
          onSaved={async ({ entryId, bankChanged, bullets, shows }) => {
            if (bankChanged) await reload(null);
            // A page's + puts the new entry where it was pressed (KAN-920):
            // a new entry lands last in its section, so it moves from there
            const place = !entryForm.target ? entryForm.place : undefined;
            if (place && entryId) {
              const { bank: nowBank, choices: nowChoices } = held.current;
              const created = nowBank.entries.find((e) => e.id === entryId);
              const ids =
                created &&
                printedSections(nowBank, nowChoices, pageNow.current.section_order)
                  .find((s) => s.entries.some((e) => e.id === entryId))
                  ?.entries.map((e) => e.id);
              const to = ids ? (place.after ? ids.indexOf(place.after) + 1 : 0) : -1;
              const changes = to >= 0 && moveTo(nowBank, nowChoices, "entry", entryId, to);
              if (changes) void apply(changes);
            }
            const entry = held.current.bank.entries.find((e) => e.id === entryId);
            if (!entry || !bullets) return;
            // A school's switches join the same change, one Undo step
            const choice = held.current.choices.entries.find((c) => c.entry_id === entry.id);
            const entries =
              shows &&
              choice &&
              (choice.show_gpa !== shows.gpa || choice.show_coursework !== shows.coursework)
                ? [
                    {
                      entry_id: entry.id,
                      show_gpa: shows.gpa,
                      show_coursework: shows.coursework,
                    },
                  ]
                : [];
            // This resume's order and boxes, as one choice change with Undo.
            // A new bullet has its id only once the bank is read again: the
            // new ones are the entry's bullets the form did not list, in the
            // order they were added
            const listed = new Set(bullets.flatMap((b) => (b.id ? [b.id] : [])));
            const fresh = entry.bullets.filter((b) => !listed.has(b.id)).map((b) => b.id);
            let n = 0;
            const rows = bullets.flatMap((b, position) => {
              const bullet_id = b.id ?? fresh[n++];
              return bullet_id ? [{ bullet_id, position, shown: !b.off }] : [];
            });
            const now = held.current.choices.bullets;
            const same = rows.every((r) => {
              const c = now.find((x) => x.bullet_id === r.bullet_id);
              return c && c.shown === r.shown && (!r.shown || c.position === r.position);
            });
            if (!same || entries.length)
              void apply({ ...(entries.length && { entries }), ...(!same && { bullets: rows }) });
          }}
        />
      )}
    </>
  );
  // The side panel's sheet on a phone (KAN-586), opened by its toolbar button
  const [phonePanel, setPhonePanel] = useState(false);
  const history: HistoryTools = {
    canUndo: steps.undo > 0 && !fittingNow,
    canRedo: steps.redo > 0 && !fittingNow,
    onUndo: () => travel(true),
    onRedo: () => travel(false),
  };
  // The open line's Move Up and Move Down, on the desktop bar and in the
  // phone's sheet: typed text goes first, so the move's render prints it
  const moves: MoveTools | null =
    line?.kind === "bullet" || line?.kind === "entry"
      ? {
          up: Boolean(move(bank, choices, line, -1)),
          down: Boolean(move(bank, choices, line, 1)),
          onMove: (by) => {
            flush();
            const changes = move(held.current.bank, held.current.choices, line, by);
            if (changes) void apply(changes);
          },
        }
      : null;
  // What the open line's tools act through, on both layouts (KAN-799)
  const handlers: LineHandlers = { moves };

  // The page as its outline (KAN-920): the sections that print, in order,
  // for the breadcrumb, the picked block's moves and the page's handles
  const printed = printedSections(bank, choices, page.section_order);
  const sectionHolding = (entryId: string) =>
    printed.find((s) => s.entries.some((e) => e.id === entryId));
  const pick = (block: Picked | null) => {
    select(null);
    setPicked(block);
  };
  /** Moves a section, an entry or a bullet to `to` among its siblings, with
   *  Undo, as any move: an entry or a bullet shows its move at once
   *  (`swapsOf`); a section is a page setting, so it moves when its PDF lands. */
  const moveBlock = (block: Picked, to: number) => {
    flush();
    if (block.kind === "section") {
      const now = pageNow.current;
      const ids = printedSections(held.current.bank, held.current.choices, now.section_order).map(
        (s) => s.id,
      );
      const from = ids.indexOf(block.id);
      if (from < 0 || to < 0 || to >= ids.length || to === from) return;
      void applyPage({
        ...now,
        section_order: sectionOrderAfter(ids, now.section_order, from, to),
      });
      return;
    }
    const changes = moveTo(held.current.bank, held.current.choices, block.kind, block.id, to);
    if (changes) void apply(changes);
  };
  /** A block's place among its siblings, for a move by one. */
  const indexOf = (block: Picked): number => {
    if (block.kind === "section") return printed.findIndex((s) => s.id === block.id);
    if (block.kind === "entry")
      return sectionHolding(block.id)?.entries.findIndex((e) => e.id === block.id) ?? -1;
    for (const section of printed)
      for (const entry of section.entries) {
        const at = entry.bullets.findIndex((b) => b.id === block.id);
        if (at >= 0) return at;
      }
    return -1;
  };
  const siblingCount = (block: Picked): number => {
    if (block.kind === "section") return printed.length;
    if (block.kind === "entry") return sectionHolding(block.id)?.entries.length ?? 0;
    const entry = printed
      .flatMap((s) => s.entries)
      .find((e) => e.bullets.some((b) => b.id === block.id));
    return entry?.bullets.length ?? 0;
  };
  // Only a block the page still prints counts as picked
  const pickedNow = picked && indexOf(picked) >= 0 ? picked : null;
  const blockMoves: MoveTools | null = pickedNow
    ? {
        up: indexOf(pickedNow) > 0,
        down: indexOf(pickedNow) < siblingCount(pickedNow) - 1,
        onMove: (by) => moveBlock(pickedNow, indexOf(pickedNow) + by),
      }
    : null;
  /** The breadcrumb's steps for the picked block or the open line: its
   *  section, then its entry, then the bullet or field itself. */
  const crumbs = ((): Crumb[] => {
    const sectionStep = (id: string, last: boolean): Crumb => ({
      label: printed.find((s) => s.id === id)?.label ?? id,
      ...(!last && { target: `section:${id}` }),
    });
    const entryStep = (entryId: string, last: boolean): Crumb[] => {
      const section = sectionHolding(entryId);
      const entry = section?.entries.find((e) => e.id === entryId);
      if (!section || !entry) return [];
      return [
        sectionStep(section.id, false),
        {
          label: entry.title || section.noun,
          ...(!last && { target: `entry:${entryId}` }),
        },
      ];
    };
    const bulletStep = (entryId: string, bulletId: string): Crumb[] => {
      const entry = sectionHolding(entryId)?.entries.find((e) => e.id === entryId);
      const n = (entry?.bullets.findIndex((b) => b.id === bulletId) ?? -1) + 1;
      return [...entryStep(entryId, false), { label: n > 0 ? `Bullet ${n}` : "Bullet" }];
    };
    if (pickedNow?.kind === "section") return [sectionStep(pickedNow.id, true)];
    if (pickedNow?.kind === "entry") return entryStep(pickedNow.id, true);
    if (pickedNow?.kind === "bullet") {
      const entry = bank.entries.find((e) => e.bullets.some((b) => b.id === pickedNow.id));
      return entry ? bulletStep(entry.id, pickedNow.id) : [];
    }
    if (line?.kind === "bullet") return bulletStep(line.entry.id, line.bullet.id);
    if (line?.kind === "entry" && box)
      return [...entryStep(line.entry.id, false), { label: kindLabel(box.kind) }];
    if (line?.kind === "skill")
      return printed.some((s) => s.id === "skills")
        ? [sectionStep("skills", false), { label: line.skill.name }]
        : [];
    return [];
  })();
  /** What Esc climbs to from the open line or the picked block. */
  const parentOf = (): Picked | null => {
    if (line?.kind === "bullet") return { kind: "entry", id: line.entry.id };
    if (line?.kind === "entry") return { kind: "entry", id: line.entry.id };
    if (line?.kind === "skill") return { kind: "section", id: "skills" };
    if (pickedNow?.kind === "bullet") {
      const entry = bank.entries.find((e) => e.bullets.some((b) => b.id === pickedNow.id));
      return entry ? { kind: "entry", id: entry.id } : null;
    }
    if (pickedNow?.kind === "entry") {
      const section = sectionHolding(pickedNow.id);
      return section ? { kind: "section", id: section.id } : null;
    }
    return null;
  };
  const keysNow: typeof keys.current = {
    climb: () => (selected || pickedNow ? pick(parentOf()) : undefined),
    nudge: (by) => {
      if (blockMoves) {
        if (by < 0 ? blockMoves.up : blockMoves.down) blockMoves.onMove(by);
        return true;
      }
      if (!moves) return false;
      if (by < 0 ? moves.up : moves.down) moves.onMove(by);
      return true;
    },
  };
  useEffect(() => {
    keys.current = keysNow;
  });
  /** What a block's + adds after it: a bullet in its entry's form, an entry
   *  in its section's, in the place after it; null where nothing can be (the
   *  skills, a Lines section). */
  const addAfter = (
    block: OutlineBlock,
  ): { noun: string; add: (opener: HTMLElement) => void } | null => {
    // A bullet's opens a new line under it, typed in on the page: the
    // entry's form for one bullet broke the editing in place (2026-11-19)
    if (block.kind === "bullet") {
      const entry = bank.entries.find((e) => e.id === block.parent);
      if (!entry) return null;
      return { noun: "Bullet", add: () => openNew(entry.id, block.id) };
    }
    // An entry's own rows (its title, organization, dates) take no +: one
    // there read as either another entry or another bullet. A section's
    // heading adds an entry, first in it; a bullet adds a bullet
    if (block.kind === "entry") return null;
    const section = printed.find((s) => s.id === block.id);
    if (!section?.addable) return null;
    return {
      noun: section.noun,
      add: (opener) =>
        openEntryForm(
          {
            target: null,
            ...sectionOf(section.id),
            place: { after: null },
          },
          opener,
        ),
    };
  };
  /** A block's menu, at its handle (KAN-920): what the Sections panel's
   *  row does for it, in its words, plus its moves, in three groups. Edit
   *  opens a bullet for typing on the page, and an entry's form for its
   *  details (dates, location), which the page does not type; Add
   *  Bullet puts an empty row in the entry's form, after the bullet or
   *  last; Remove From Resume is the panel's hide, with Undo, the bank
   *  keeping it. A section has no Edit: its heading has nothing to type. */
  const actionsOf = (block: OutlineBlock): BlockAction[] => {
    const at = { kind: block.kind, id: block.id };
    const index = indexOf(at);
    const moves: BlockAction[] = [
      {
        key: "up",
        text: "Move Up",
        group: "move",
        icon: <ArrowUpIcon aria-hidden />,
        disabled: index <= 0,
        onClick: () => moveBlock(at, index - 1),
      },
      {
        key: "down",
        text: "Move Down",
        group: "move",
        icon: <ArrowDownIcon aria-hidden />,
        disabled: index < 0 || index >= siblingCount(at) - 1,
        onClick: () => moveBlock(at, index + 1),
      },
    ];
    const remove = (changes: ChoicesUpdate): BlockAction => ({
      key: "remove",
      text: "Remove From Resume",
      group: "remove",
      icon: <TrashIcon />,
      onClick: () => {
        setPicked(null);
        void apply(changes);
      },
    });
    if (block.kind === "bullet") {
      const add = addAfter(block);
      return [
        {
          key: "edit",
          text: "Edit Bullet",
          group: "change",
          icon: <PencilIcon />,
          onClick: () => select(`${block.id}.bullet`),
        },
        ...(add
          ? [
              {
                key: "add",
                text: "Add Bullet Below",
                group: "change" as const,
                icon: <PlusIcon />,
                onClick: add.add,
              },
            ]
          : []),
        ...moves,
        remove({ bullets: [{ bullet_id: block.id, shown: false }] }),
      ];
    }
    if (block.kind === "entry") {
      const entry = bank.entries.find((e) => e.id === block.id);
      if (!entry) return moves;
      const noun = printed.find((s) => s.id === block.parent)?.noun ?? "Entry";
      const form = (opener: HTMLElement, newBulletAfter?: string) =>
        openEntryForm(
          {
            target: entry,
            section: entry.section,
            customSectionId: entry.custom_section_id ?? null,
            newBulletAfter,
          },
          opener,
        );
      return [
        {
          key: "edit",
          text: `Edit ${noun}`,
          group: "change",
          icon: <PencilIcon />,
          onClick: (opener) => form(opener),
        },
        {
          key: "add",
          text: "Add Bullet",
          group: "change",
          icon: <PlusIcon />,
          // A new line under its last bullet on this resume, typed in on the
          // page; an entry that shows none has no line to open it under, so
          // its form opens on an empty row
          onClick: (opener) => {
            const last = shownBullets(entry, choices).at(-1);
            if (last) openNew(entry.id, last.id);
            else form(opener, "");
          },
        },
        ...moves,
        remove({ entries: [{ entry_id: block.id, shown: false }] }),
      ];
    }
    const section = printed.find((s) => s.id === block.id);
    const add = addAfter(block);
    return [
      ...(add
        ? [
            {
              key: "add",
              text: `Add ${add.noun}`,
              group: "change" as const,
              icon: <PlusIcon />,
              onClick: add.add,
            },
          ]
        : []),
      ...moves,
      remove(
        block.id === "skills"
          ? {
              skills: choices.skills
                .filter((c) => c.shown)
                .map((c) => ({ skill_id: c.skill_id, shown: false })),
            }
          : { entries: (section?.entries ?? []).map((e) => ({ entry_id: e.id, shown: false })) },
      ),
    ];
  };
  // The page's own handles, on the editor's own page (not Tailor's review,
  // whose page is for reading its changes)
  const pageOutline: PageOutline | undefined = suggestions
    ? undefined
    : {
        blocksOf: (boxes) => outlineOf(boxes, bank, choices, page.section_order),
        picked: pickedNow,
        onPick: (block) => pick({ kind: block.kind, id: block.id }),
        onMove: (block, to) => moveBlock(block, to),
        addOf: addAfter,
        actionsOf,
      };
  if (phone) {
    const start = line && box && startText(line, box);
    // A bullet's field is a rich one, as on the desktop, so the sheet's bold
    // and italic show in its words (KAN-799); it was a textarea showing the
    // markers. Other lines keep the sheet's own plain field
    const bulletField =
      line?.kind === "bullet" && box && selected && start != null
        ? () =>
            richLine(drafts[selected] ?? start, (text) => type(selected, text), {
              "aria-label": kindLabel(box.kind),
              attach: () => undefined,
              onBlur: () => flush(),
              onKeyDown: (e) => {
                if (e.key !== "Enter") return;
                e.preventDefault();
                e.currentTarget.blur();
              },
              className: cn(PHONE_FIELD, "min-h-24"),
            })
        : null;
    return (
      <>
        <PhoneEditor
          rendered={rendered}
          title={<TitleHistoryContext value={titleHistory}>{heading}</TitleHistoryContext>}
          pages={pdfPane((pdf) => (
            <PdfPages
              pdf={pdf.pdf}
              boxes={pdf.boxes}
              selected={selected}
              onSelect={onLine}
              onDrawn={drawn}
              swaps={swapsOn}
              gaps={gapsOn}
              placeholder={<PageSkeleton />}
              marks={marks}
              focus={focus}
              dots={dots}
              onDot={onDot}
            />
          ))}
          bank={bank}
          choices={choices}
          selected={selected}
          line={line}
          box={box}
          text={start == null ? null : (drafts[selected!] ?? start)}
          bulletField={bulletField}
          saving={saving || fittingNow}
          fitting={fittingNow}
          error={error}
          download={download}
          more={more}
          bar={phoneBar}
          back={phoneBack}
          page={page}
          onPage={applyPage}
          suggestions={
            reviewing && {
              count: suggestionCount,
              panel,
              open: suggestionsOpen,
              onOpenChange: setSuggestionsOpen,
            }
          }
          handlers={handlers}
          assistant={assistant("h-full")}
          panel={{
            open: phonePanel,
            onOpenChange: setPhonePanel,
            tab,
            onTab: setTab,
            sections: sectionsOutline,
          }}
          onSelect={select}
          onType={(text) => selected && type(selected, text)}
          onFlush={() => flush()}
          onApply={apply}
          onFit={fit}
          history={history}
          cuts={cuts}
        />
      </>
    );
  }

  const bar = (
    <Bar
      line={line}
      box={box}
      crumbs={crumbs}
      onCrumb={(target) => {
        // At the first colon: a custom section's id has its own ("custom:x")
        const at = target.indexOf(":");
        pick({ kind: target.slice(0, at) as BlockKind, id: target.slice(at + 1) });
      }}
      choices={choices}
      handlers={handlers}
      rendered={rendered}
      saving={saving || fittingNow}
      fitting={fittingNow}
      onFit={fit}
      // The toolbar's ?, on the editor's own page (not Tailor's review)
      onTour={suggestions ? undefined : () => setWalking(true)}
      experiences={
        // They wait for the first render, since a pick renders again
        rendered
          ? {
              // Not on Tailor's review: choosing what a resume shows is the
              // editor's own page's work, a run's own removals have Undo, and
              // a toolbar button and modal for it there cluttered the review
              picker: suggestions
                ? null
                : { open: scoutOpen && panelView === "experiences", onToggle: showExperiences },
              // On both pages, since both have Fit: only while something it
              // cut is still off the page, or its panel is open
              cut:
                cutOpen || cutLeft(bank, choices, cuts)
                  ? {
                      open: cutOpen,
                      onToggle: () =>
                        suggestions ? showSide(cutOpen ? null : "cut") : showPanel("cut"),
                    }
                  : null,
            }
          : null
      }
      zoom={{ zoom, onZoom: setZoom }}
      history={history}
      format={{
        page,
        disabled: !rendered,
        onChange: applyPage,
        panelOpen,
        onPanel: togglePanel,
      }}
    />
  );
  // The two resumes side by side only read: a plain heading over each in
  // place of the toolbar, no click targets and no marks. They scroll with
  // the page, together, so a line stays level with its twin. The tailored
  // one kept its toolbar, and the original a card with a Read Only tag and a
  // scroll of its own, until the user found that heavy for a comparison
  const comparing = Boolean(shownOriginal);
  const compareHeading = "text-label text-ink font-semibold";

  const grid = (
    <div
      className={cn(
        "grid items-start gap-5",
        // The column docks beside the page from @6xl only; below it floats
        // over the page (`floating`)
        (shownPanel || shownTabs || shownCut) && "@6xl/main:grid-cols-[minmax(0,1fr)_24rem]",
        // The two resumes at one width, so a line reads against its twin
        shownOriginal && "@4xl/main:grid-cols-2",
      )}
    >
      {/* Placed, so a column floating in the same cell never pushes it down */}
      <div className="flex min-w-0 flex-col gap-2 @4xl/main:col-start-1 @4xl/main:row-start-1">
        {comparing ? (
          <div className="flex min-h-9 items-center">
            <h2 className={compareHeading}>Tailored Resume</h2>
          </div>
        ) : (
          bar
        )}
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <div
          ref={pages}
          data-keeps-selection
          className="mx-auto w-full"
          style={{ maxWidth: zoomWidth(zoom) }}
          onPointerDownCapture={(e) => {
            const origin = e.currentTarget.getBoundingClientRect();
            pressed.current = { x: e.clientX - origin.left, y: e.clientY - origin.top };
          }}
          // A press on the paper off every line saves the open line and
          // closes it, as a press off the page does: the page keeps the
          // selection for its lines, so until then only Enter or Escape
          // left a line once it was open. A line's own target opens that
          // line, and the field and the margin dots keep it. So does a
          // block's menu (KAN-920): React passes a press in its portal up
          // through the page, and it let go of the block it acts on
          onPointerDown={(e) => {
            if (
              !(e.target as Element).closest(
                "[data-box], [data-popup], input, textarea, button, [contenteditable], [data-block-menu]",
              )
            ) {
              select(null);
              setPicked(null);
            }
          }}
        >
          {pdfPane((pdf) => (
            <PdfPages
              pdf={pdf.pdf}
              boxes={pdf.boxes}
              readOnly={comparing}
              popup={selected && popupNode ? { line: selected, node: popupNode } : undefined}
              selected={selected}
              onSelect={onLine}
              overlay={overlay}
              overlaid={overlaid}
              shiftOf={shiftOf}
              inserts={insertsOn}
              swaps={swapsOn}
              gaps={gapsOn}
              onDrawn={drawn}
              placeholder={<PageSkeleton />}
              outline={pageOutline}
              marks={showMarks ? allMarks : undefined}
              lit={lit}
              focus={showMarks ? focus : undefined}
            />
          ))}
        </div>
      </div>
      {/* The assistant lives in Scout's panel, opened from the top bar's
          Scout (`ScoutTakeover`), so the page has one way to it. Not on
          Tailor's review, whose Scout stays the job search chat. Kept
          mounted while the panel is closed, so the chat survives closing
          it; marked KEEPS_SELECTION, since the panel sits outside the
          editor and the assistant acts on the selected line. It docked
          beside the page from a toolbar Ask Scout until KAN-411; the user
          found two Scout buttons on one page one too many. It waits for the
          first render, as that button did: the assistant reads its page
          count and acts through renders, so until then the panel is
          Scout's job chat. The Experiences picker shares the panel (KAN-440):
          the toolbar's Experiences opens it, and the top bar's Scout goes
          back to the assistant, which stays mounted under it, for its chat.
          It floats over the page below xl (`float`, KAN-576): docked at
          1024, it left the resume a 416px column with about 4px text.
          While ASK_SCOUT_LIVE is off the assistant is off too, as on the
          phone: the panel takes over only for the toolbar's own views, so a
          panel left open on another page shows nothing here instead of the
          assistant */}
      {rendered && !suggestions && (ASK_SCOUT_LIVE || panelView !== "scout") && (
        <ScoutTakeover
          float
          bare={tabbed(panelView)}
          mark={
            panelView === "experiences"
              ? EXPERIENCES_MARK
              : panelView === "cut"
                ? CUT_MARK
                : undefined
          }
          away={panelView !== "scout" ? showScout : undefined}
          title={
            panelView === "experiences"
              ? "Experiences"
              : panelView === "cut"
                ? "Cut From Resume"
                : panelView === "format"
                  ? "Format Options"
                  : panelView === "sections"
                    ? "Sections"
                    : "Scout"
          }
          subtitle={
            panelView === "experiences"
              ? "Pick what this resume shows"
              : panelView === "cut"
                ? "Put back what Fit to One Page hid"
                : panelView === "format"
                  ? "Set how this page prints"
                  : panelView === "sections"
                    ? "Drag to change the order"
                    : "Edits this resume as you talk"
          }
        >
          <div data-keeps-selection className="flex min-h-0 flex-1 flex-col">
            <div className={cn("flex min-h-0 flex-1 flex-col", panelView !== "scout" && "hidden")}>
              {ASK_SCOUT_LIVE && assistant("flex-1")}
            </div>
            {panelView === "experiences" && (
              <div
                data-tour="experiences-panel"
                className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-none px-4 pt-2 pb-4"
              >
                {sample ? (
                  <>
                    <Notice Icon={StackIcon}>
                      Practice: these are examples. Nothing you tick here is saved.
                    </Notice>
                    <ExperiencesPicker
                      bank={SAMPLE_BANK}
                      choices={sample}
                      opened={["experience", "projects", "skills"]}
                      onApply={(changes) => setSample((s) => s && mergeChoices(s, changes))}
                    />
                  </>
                ) : (
                  <ExperiencesPicker
                    key={walkChapter === "reuse" ? "walk" : "own"}
                    bank={bank}
                    choices={choices}
                    onApply={apply}
                    // The walkthrough's step opens every group, so its ring has
                    // a box to land on
                    opened={walkChapter === "reuse" ? ["education", "experience", "projects"] : []}
                  />
                )}
              </div>
            )}
            {panelView === "cut" && (
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-none px-4 pt-2 pb-4">
                <CutPicker bank={bank} choices={choices} cuts={cuts} onApply={apply} />
              </div>
            )}
            {tabbed(panelView) && (
              <>
                <div className="shrink-0 px-4 pt-3">
                  <PanelTabs tab={tab} onTab={showTab} onClose={closeScout} />
                </div>
                <div
                  data-tour="panel-body"
                  className="relative flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto overscroll-none px-4 pt-3 pb-4"
                >
                  {panelView === "sections" ? (
                    sectionsOutline
                  ) : (
                    <FormatOptions page={page} onChange={applyPage} />
                  )}
                </div>
              </>
            )}
          </div>
        </ScoutTakeover>
      )}
      {/* Tailor's suggestions, above the page on a narrow screen. */}
      {/* The panel scrolls its own list under its header, so the column
          only caps its height: scrolled here, the header and the panel's
          rounded corners went up with the list. The cap is measured
          (`useFitToWindow`): a fixed one, the window less 15rem, ran the
          panel's foot below the window before the page scrolled and left a
          gap under it after, once the title row grew.
          Below @6xl it floats over the page's right side in the page's own
          cell (KAN-576), under the 44px bar, with `shadow-lift`: docked at
          1024, the 384px column left the resume about 480px wide */}
      {(shownPanel || shownTabs || shownCut) && (
        <div
          data-keeps-selection
          ref={fitPanel}
          className={cn(
            "max-h-scroll-box -order-1 flex flex-col @4xl/main:sticky @4xl/main:order-none @4xl/main:max-h-(--fit-height)",
            FLOATING,
          )}
        >
          {shownTabs ? (
            <section
              aria-label="Side Panel"
              className="sm:bg-brand-tint sm:ring-brand-pale sm:rounded-card flex min-h-0 flex-col gap-3 sm:p-3 sm:ring-1"
            >
              <PanelTabs tab={tab} onTab={showTab} onClose={() => showSide(null)} />
              <div className="relative -mr-1.5 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-none pr-1.5">
                {side === "sections" ? (
                  sectionsOutline
                ) : (
                  <FormatOptions page={page} onChange={applyPage} />
                )}
              </div>
            </section>
          ) : shownCut ? (
            <SidePanel title="Cut From Resume" onClose={() => showSide(null)}>
              <CutPicker bank={bank} choices={choices} cuts={cuts} onApply={apply} />
            </SidePanel>
          ) : (
            shownPanel
          )}
        </div>
      )}
      {/* The original beside the page; under it on a narrow screen */}
      {shownOriginal && (
        <section className="flex min-w-0 flex-col gap-2">
          {/* Its X closes the column, as the Suggestions panel's does: the
              toolbar is gone here, so this is the way out */}
          <div className="flex min-h-9 items-center justify-between">
            <h2 className={compareHeading}>Original Resume</h2>
            <IconButton
              place="row"
              label="Close Comparison"
              tooltip={false}

              onClick={() => showSide(null)}
            >
              <CloseIcon />
            </IconButton>
          </div>
          {shownOriginal}
        </section>
      )}
    </div>
  );
  // The title spans the page and the column beside it, so the column starts
  // level with the toolbar, as Docs' comments start level with its bar, and
  // on Tailor's review the document's actions sit at its right, as Docs' do. The
  // toolbar spanned both too for a day, which put the panel under it, apart
  // from the page it reviews
  return (
    <div className={cn("flex flex-col", suggestions ? "mt-2 gap-2" : "mt-4 gap-3")}>
      {/* The title row (KAN-799): the resume and its file, the name at the
          left, then the review's columns and Download,
          the page's one filled button (secondary on Tailor's review, whose
          fill is Finish), at the right, then on the editor's own page the
          resume's ⋯ (KAN-825), as an upload's page has. Download sat in
          the bar until then, among the tools. A "Saving…" and "Saved" status
          stood before Download until 2026-11-19: the user found it a
          developer's tool, a watch on how long a save took; a save that
          fails says so under the bar, and Fit says "Fitting…" itself */}
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <TitleHistoryContext value={titleHistory}>{heading}</TitleHistoryContext>
        </div>
        {reviewing && (
          <div className="flex shrink-0 items-center gap-1">
            <ReviewButtons
              review={{
                count: suggestionCount,
                side,
                onSide: showSide,
                hasOriginal: Boolean(original),
              }}
            />
          </div>
        )}
        <span data-tour="download" className="flex shrink-0">
          <DownloadMenu download={download} secondary={Boolean(suggestions)} />
        </span>
        {more}
      </div>
      <DownloadNotes download={download} />
      {walking && !suggestions && (
        <Walkthrough
          api={walkApi}
          onChapter={setWalkChapter}
          onClose={() => {
            setWalking(false);
            setSample(null);
            onTourEnd?.();
          }}
        />
      )}
      {grid}
    </div>
  );
}

/**
 * A sticky column's height cap, as `--fit-height` on it: the window below
 * its top, less a 24px foot. Read again on any scroll (the page scrolls in
 * `main`, not the window, so the listener captures) and on resize, once a
 * frame. Before the page scrolls the column's top sits under the title
 * row; stuck, at its `top`; a fixed cap fitted one and not the other.
 * Its top is read no higher than where it sticks: at the page's end the
 * grid pushes a sticky column up past that, and reading that top grew the
 * cap, so the panel kept growing as the page scrolled. Never under 240px,
 * so a short window still shows the panel's top.
 */
function useFitToWindow(foot = 24) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (!el) return;
    let frame = 0;
    const fit = () => {
      frame = 0;
      const stuck =
        (el.closest("main")?.getBoundingClientRect().top ?? 0) +
        (parseFloat(getComputedStyle(el).top) || 0);
      const room = window.innerHeight - Math.max(el.getBoundingClientRect().top, stuck) - foot;
      el.style.setProperty("--fit-height", `${Math.max(240, Math.round(room))}px`);
    };
    const queue = () => {
      if (!frame) frame = requestAnimationFrame(fit);
    };
    fit();
    document.addEventListener("scroll", queue, { capture: true, passive: true });
    window.addEventListener("resize", queue);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("scroll", queue, { capture: true });
      window.removeEventListener("resize", queue);
    };
  }, [el, foot]);
  return setEl;
}

/** The review's column from @4xl to @6xl: in the page's cell, at its right,
 *  over the page, below the 44px bar (`SLIM_BAR`) at rest and when stuck.
 *  From @6xl it docks in the grid's second column, level with the bar. */
const FLOATING = cn(
  "@4xl/main:col-start-1 @4xl/main:row-start-1 @4xl/main:z-30 @4xl/main:mt-13 @4xl/main:top-15 @4xl/main:w-96 @4xl/main:justify-self-end @4xl/main:rounded-card @4xl/main:shadow-lift",
  "@6xl/main:col-start-2 @6xl/main:z-auto @6xl/main:mt-0 @6xl/main:top-2 @6xl/main:w-auto @6xl/main:justify-self-stretch @6xl/main:shadow-none",
);

/**
 * Where the first PDF is drawn, while the page's render is on its way: it
 * suspends on the render (the editor wraps it in a <Suspense> over a
 * PageSkeleton), then hands a PDF to the editor, which draws it from then
 * on, or shows why it did not come (the page area says so). The same skeleton stays up for the one
 * frame before the editor takes it.
 */
function FirstRenderPane({
  initial,
  onLoad,
  resumeId,
}: {
  initial: FirstRender;
  onLoad: (pdf: RenderedPdf) => void;
  resumeId: string;
}) {
  const { data, error } = use(initial);
  useEffect(() => {
    if (data) onLoad(data);
  }, [data, onLoad]);

  if (data) return <PageSkeleton />;
  return (
    <EmptyState
      Icon={CloudSlashIcon}
      title="This Resume Isn't Loading Right Now"
      action={
        // A plain link: a full reload is what renders it again.
        <a
          href={`/resumes/${encodeURIComponent(resumeId)}`}
          className={buttonClasses({ variant: "secondary", size: "sm" })}
        >
          Try Again
        </a>
      }
    >
      {error}
    </EmptyState>
  );
}

/**
 * The desktop editor before anything has loaded, for ./loading.tsx: the
 * title row's title and Download, then the slim bar's box with Undo and Redo
 * and its end (the panels and the zoom) as bars, over a page's skeleton, in
 * the editor's own layout, so the editor that replaces it keeps every edge
 * where it was.
 */
export function EditorSkeleton() {
  return (
    <div aria-hidden="true" className="mt-4 flex flex-col gap-3">
      {/* The title's height (`ResumeTitle`'s h1), Download and ⋯ */}
      <div className="flex h-9 items-center gap-3 @3xl/main:h-10">
        <Skeleton className="h-6 w-56 max-w-full @3xl/main:h-8" />
        <Skeleton className="ml-auto h-9 w-28" />
        <Skeleton className="size-8 rounded-full" />
      </div>
      <div className="flex min-w-0 flex-col gap-2">
        <div className={SLIM_BAR}>
          <Skeleton className="h-6 w-14" />
          <Skeleton className="ml-auto h-7 w-40" />
        </div>
        <PageSkeleton />
      </div>
    </div>
  );
}
