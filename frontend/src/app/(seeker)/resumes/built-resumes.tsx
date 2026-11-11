"use client";

import { FileTextIcon, TagIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import {
  startTransition,
  useEffect,
  useEffectEvent,
  useOptimistic,
  useRef,
  useState,
  useTransition,
} from "react";

import { FieldFacet, type FacetOption } from "@/components/field-facet";
import { AllFiltersButton, ClearFiltersButton } from "@/components/filter-actions";
import { matches, RESUME_TYPES, searchWords, type ResumeType } from "@/components/resume-list";
import { RESUME_TYPE_ICON } from "@/components/resume-row";
import { CompanyIcon, SearchIcon } from "@/components/icons";
import { GroupHeadingRow, useFolds } from "@/components/table-group";
import { GroupByOptions, TableSettingsMenu } from "@/components/table-settings";
import { useShallowParams, useShallowPush } from "@/components/shallow-routing";
import { SortMenu } from "@/components/sort-menu";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchField } from "@/components/ui/search-field";
import { SegmentedToggle } from "@/components/ui/segmented-control";
import { viewOption } from "@/components/views";
import { readEvents } from "@/components/scout/stream";
import {
  listBuiltResumes,
  startFromResume,
  type BuiltResume,
  type GenerateStreamEvent,
} from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { listResumes, type ResumeItem } from "@/lib/resume-actions";
import { MAX_UPLOADS } from "@/lib/resume-limits";
import { markResumesStale, takeResumesStale } from "@/lib/resumes-stale";

import { setResumesLayout } from "./actions";
import { BuiltResumeRow } from "./built-resume-row";
import { DuplicateResumeDialog, type Duplicate } from "./duplicate-resume-dialog";
import { GenerateRunning, type GenerateStep } from "./generate-running";
import { SearchFacet } from "../applications/field-filters";
import { RESUMES_SEARCH, ResumesHeader } from "./header";
import {
  RESUME_GROUP_BY,
  ResumeAllFilters,
  setResumeGroupBy,
  useResumeGroupBy,
  type ResumePicks,
} from "./resume-filters";
import type { Source } from "../jobs/resume-picker";
import { NewResumeDialog } from "./new-resume-dialog";
import { ResumeList } from "./resume-list";
import { ShortLabel, UploadedRow, useResumeUpload } from "./upload-resume";
import type { ResumesLayout } from "./view";

/** The Type filter's options, each with its type's glyph. */
const TYPES: FacetOption[] = RESUME_TYPES.map((type) => ({
  ...type,
  Icon: RESUME_TYPE_ICON[type.value],
  iconClassName: "text-ink-meta",
}));

/** `?type=uploaded,tailored`: the picked types, in the options' order;
 *  none (or none valid) is every type. */
function parseTypes(raw: string | null): ResumeType[] {
  const picked = raw?.split(",") ?? [];
  return TYPES.map((t) => t.value).filter((v) => picked.includes(v)) as ResumeType[];
}

/** The list's orders, in `?sort=`: Date Modified (newest first, the
 *  default, with no `?sort=`; "Last Edited" until 2026-11-10, renamed with
 *  the cards' column), Recently Created (`created`, newest made first),
 *  Oldest First, and Name (A to Z). For the modified orders an upload dates
 *  from its upload, a built resume from its last edit. */
type Sort = "edited" | "created" | "oldest" | "name";

const SORTS: { value: Sort; label: string }[] = [
  { value: "edited", label: "Date Modified" },
  // The newest made first, whatever was edited since (2026-11-10)
  { value: "created", label: "Recently Created" },
  { value: "oldest", label: "Oldest First" },
  { value: "name", label: "Name (A to Z)" },
];

function parseSort(raw: string | null): Sort {
  return raw === "created" || raw === "oldest" || raw === "name" ? raw : "edited";
}

/** One resume of either kind, as the list orders and filters it. */
type Row =
  | {
      key: string;
      type: "uploaded";
      name: string;
      at: string;
      /** When it was uploaded or made: the Created column's instant. */
      created: string;
      text: string;
      primary: boolean;
      /** The job posting's company, a tailored resume's only. */
      company: null;
      upload: ResumeItem;
    }
  | {
      key: string;
      type: "generated" | "tailored";
      name: string;
      at: string;
      created: string;
      text: string;
      primary: boolean;
      company: string | null;
      built: BuiltResume;
    };

const readLists = () => Promise.all([listBuiltResumes(), listResumes()]);
type Lists = Awaited<ReturnType<typeof readLists>>;

/**
 * Documents' Resumes tab (KAN-766): its header, then one list of
 * every resume the student has (KAN-362), uploaded, generated (the base
 * resumes, KAN-207) and tailored (KAN-217), in the order the Sort dropdown
 * picks (`SortMenu`, KAN-366; newest first by default), each as its
 * card with its star, Rename, Download and Delete, in a card that scrolls
 * inside itself (./resume-list.tsx). Every card acts alike, so one list
 * holds them all; each says what it is in its own line ("Uploaded …",
 * "Made from your experiences", "<posting> at <company>").
 *
 * The list and the grid hold the same rows in the same order, the starred
 * resume first, with no groups by default (2026-11-10). The list was
 * grouped by type from KAN-404 (Uploaded, Generated, Tailored, each under a
 * heading with a count that folded it, in `?collapsed=`) until the grid
 * came without groups: the user found the headings ugly beside it and the
 * Type filter enough to find one type. Table Settings' Group By Type
 * groups the list again, under the shared quiet heading
 * (./resume-filters.tsx). The list is one scroll (./resume-list.tsx): no
 * scroll box per type and no Show N More, which the user turned down.
 *
 * It is laid out as the Applications Tracker is (../applications/page.tsx
 * and filter-bar.tsx), with the toolbar every page table has
 * (frontend/docs/design.md), so the pages read as one app: a search over
 * the names and the postings, with Upload Resume (./upload-resume.tsx),
 * Generate Resume and the layout at its right; then the Type and Company
 * filters (`FieldFacet`, `SearchFacet`, the Tracker's dropdowns) and Sort,
 * with Clear, All Filters and, in the list, Table Settings at the right;
 * then the list, or an `EmptyState` in its place. The type, the companies
 * and the order are the URL's (`?type=`, `?company=`, `?sort=`), moved in
 * place and replacing the entry
 * (`useShallowPush`), so a reload or a shared link keeps them and a tick
 * is not a step of Back. The
 * search's words are the page's own.
 *
 * It went through five shapes in KAN-362 first: three cards stacked one
 * under another, which a student with many resumes scrolled past; a pill
 * switcher under the header's own; underline tabs with counts; a table
 * with Type and Last Edited columns and sort headings; and that table
 * with the icons in one `⋯` menu. The views split one list in three, the
 * columns said what each card's line already says, and the menu hid the
 * actions a student uses. Generate Resume sat in the header until then.
 * The resume picker (`../jobs/resume-picker.tsx`) still splits Generated
 * (base and tailored) from Uploaded.
 *
 * Generate makes a base resume from the whole bank in Jake's Resume, named
 * "Resume #N" by the API until the student renames it, and opens it in the
 * editor for the student to review (KAN-444). A Type filter that would hide
 * it is cleared, so a Back finds it at the top of the list, under the
 * starred resume if that is there. Generate has no limit:
 * only uploads count toward the 5 (KAN-268). A failed Generate or reload
 * shows its error under the filter row. A Generate or an upload that would
 * make a resume the student already has (the API's 409, KAN-267) makes
 * nothing and says so in one pop-up (./duplicate-resume-dialog.tsx).
 */
export function BuiltResumes({
  initial,
  initialUploaded,
  layout,
}: {
  initial: BuiltResume[];
  initialUploaded: ResumeItem[];
  /** List or Grid (KAN-766), the student's kept choice (./view.ts). */
  layout: ResumesLayout;
}) {
  const router = useRouter();
  // The layout picked, shown at once; the action keeps it in a cookie.
  const [shownLayout, showLayout] = useOptimistic(layout);
  const [, startLayout] = useTransition();
  function pickLayout(next: ResumesLayout) {
    startLayout(async () => {
      showLayout(next);
      await setResumesLayout(next);
    });
  }
  const grid = shownLayout === "grid";
  const [resumes, setResumes] = useState(initial);
  const [uploaded, setUploaded] = useState(initialUploaded);
  // Generate's step while it runs (KAN-444), null otherwise
  const [generating, setGenerating] = useState<GenerateStep | null>(null);
  // Whether Generate's dialog shows: only once the duplicate check has
  // passed or been confirmed, so a copy is asked about before any
  // "Generating Your Resume" (the user's call, 2026-11-10). Until then the
  // button says "Checking…".
  const [showSteps, setShowSteps] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Generate Resume's dialog: the ways to start a resume.
  const [creating, setCreating] = useState(false);
  // The resume a Generate or an upload would copy, while its modal is open.
  const [duplicate, setDuplicate] = useState<Duplicate | null>(null);
  const [query, setQuery] = useState("");
  const params = useShallowParams();
  const push = useShallowPush();
  const types = parseTypes(params.get("type"));
  // `?company=A&company=B`: a name may hold a comma.
  const companies = params.getAll("company");
  const sort = parseSort(params.get("sort"));
  const groupBy = useResumeGroupBy();
  const [folded, fold] = useFolds();
  const [allOpen, setAllOpen] = useState(false);
  // Clear leaves with the last pick, so its press hands focus here.
  const allButton = useRef<HTMLButtonElement>(null);

  // The type and the sort ride in the URL together, each left out at its
  // default, replacing the entry so a tick is not a step of Back.
  function move(next: { types?: ResumeType[]; companies?: string[]; sort?: Sort }) {
    const search = new URLSearchParams();
    const t = next.types ?? types;
    const o = next.sort ?? sort;
    if (t.length > 0) search.set("type", t.join(","));
    for (const company of next.companies ?? companies) search.append("company", company);
    if (o !== "edited") search.set("sort", o);
    const qs = search.toString();
    push(qs ? `/resumes?${qs}` : "/resumes", undefined, { replace: true });
  }
  const setTypes = (next: ResumeType[]) => move({ types: next });

  // Both lists, every time: one primary star spans them.
  async function reload() {
    show(await readLists());
  }
  function show([built, uploads]: Lists) {
    if (built.data) setResumes(built.data);
    if (!uploads.error) setUploaded(uploads.resumes);
    setError(built.error ?? uploads.error);
  }

  // A Back here shows the router's copy of the list, from before the editor
  // or Tailor changed a resume; those mark it stale rather than clearing the
  // copy (lib/resumes-stale.ts), so the list is read again once.
  const showRead = useEffectEvent(show);
  useEffect(() => {
    if (takeResumesStale()) void readLists().then(showRead);
  }, []);

  // A deleted resume leaves the list first and the delete runs behind it
  // (KAN-388). A failed delete ends the transition with the row still in
  // its list, so it comes back, with the error above the list: its own
  // error line went with it. A delete that worked drops the row from its
  // list before the reload, which a failed reload would otherwise undo;
  // the reload still runs, since the star can move.
  const [gone, hide] = useOptimistic<string[], string>([], (keys, key) => [...keys, key]);
  function remove(key: string, send: () => Promise<{ error: string | null }>) {
    setError(null);
    startTransition(async () => {
      hide(key);
      const { error } = await send();
      if (error) return setError(error);
      setUploaded((rows) => rows.filter((r) => `uploaded:${r.id}` !== key));
      setResumes((rows) => rows.filter((r) => `built:${r.id}` !== key));
      await reload();
    });
  }

  const upload = useResumeUpload({
    uploaded,
    reload,
    onDuplicate: (id, name) =>
      setDuplicate({ kind: "upload", name, resume: uploaded.find((r) => r.id === id) }),
  });

  // Streamed through /api/resume-generate, so the dialog shows each step
  // as the API starts it (KAN-444). The dialog opens once the API says
  // `saving`, its check passed; a copy opens the duplicate modal instead.
  // `allowDuplicate`: the student confirmed a copy, so the API skips the
  // check and the dialog opens at once.
  async function generate(allowDuplicate = false) {
    setGenerating("reading");
    setShowSteps(allowDuplicate);
    setError(null);
    const failed = (message: string) => {
      setGenerating(null);
      setShowSteps(false);
      setError(message);
    };
    let made: BuiltResume | null = null;
    try {
      const res = await fetch("/api/resume-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(allowDuplicate ? { allow_duplicate: true } : {}),
      });
      if (!res.ok || !res.body) {
        const body: unknown = await res.json().catch(() => null);
        const detail = (body as { detail?: unknown } | null)?.detail;
        return failed(typeof detail === "string" ? detail : "Generate failed. Try again.");
      }
      for await (const event of readEvents<GenerateStreamEvent>(res.body)) {
        if (event.type === "phase") {
          setGenerating(event.phase);
          if (event.phase === "saving") setShowSteps(true);
        } else if (event.type === "error") {
          if (event.status !== 409) return failed(event.message);
          setGenerating(null);
          setShowSteps(false);
          return setDuplicate({
            kind: "generate",
            name: event.name ?? "One of your resumes",
            resume: resumes.find((r) => r.id === event.built_resume_id),
          });
        } else made = event.resume;
      }
    } catch {
      return failed("WorkIt couldn't reach its server. Try again in a minute.");
    }
    // A stream that ends with no last line lost its connection midway.
    if (!made) return failed("Generate stopped before it finished. Try again.");
    // A route handler cannot clear the router's copies (lib/resumes-stale.ts),
    // so a Back here reads the list again, the new resume in it.
    markResumesStale();
    // A Back also finds it in view: a Type filter that hides it is cleared.
    if (types.length > 0 && !types.includes("generated")) move({ types: [] });
    // The student reviews it in the editor, as a Tailor run ends: on this
    // list it was one more row to find and open. The dialog stays until the
    // editor's page takes over.
    setGenerating("opening");
    router.push(`/resumes/${encodeURIComponent(made.id)}`);
  }

  /** Start With a Resume You Have (./new-resume-dialog.tsx): the copy, then the
   *  editor, as Generate ends. Its error goes back to the dialog. */
  async function copyResume(source: Source): Promise<string | null> {
    const { data, error } = await startFromResume(
      "builtResumeId" in source
        ? { built_resume_id: source.builtResumeId }
        : { uploaded_resume_id: source.uploadedResumeId },
    );
    if (error || !data) return error ?? "Couldn't copy the resume. Try again.";
    // A Back here reads the list again and finds the copy in view.
    markResumesStale();
    if (types.length > 0 && !types.includes("generated")) move({ types: [] });
    router.push(`/resumes/${encodeURIComponent(data.id)}`);
    return null;
  }

  const rows: Row[] = [
    ...uploaded.map((r) => ({
      key: `uploaded:${r.id}`,
      type: "uploaded" as const,
      name: r.original_filename ?? "Resume",
      at: r.created_at ?? "",
      created: r.created_at ?? "",
      text: r.original_filename ?? "Resume",
      primary: r.is_default,
      company: null,
      upload: r,
    })),
    ...resumes.map((r) => ({
      key: `built:${r.id}`,
      type: r.job_posting_id ? ("tailored" as const) : ("generated" as const),
      name: r.name,
      at: r.edited_at,
      created: r.created_at,
      text: `${r.name} ${r.posting_title ?? ""} ${r.posting_company ?? ""}`,
      primary: r.is_default,
      company: r.job_posting_id ? r.posting_company : null,
      built: r,
    })),
  ].filter((row) => !gone.includes(row.key));
  const words = searchWords(query);
  /** The rows `picks` and the search let through. */
  const pass = (picks: ResumePicks) =>
    rows
      .filter((row) => picks.types.length === 0 || picks.types.includes(row.type))
      .filter(
        (row) =>
          picks.companies.length === 0 ||
          (row.company != null && picks.companies.includes(row.company)),
      )
      .filter((row) => matches(row.text, words));
  // Company's options: the companies the tailored resumes were made for.
  const companyOptions = [
    ...new Set(rows.flatMap((row) => (row.company ? [row.company] : []))),
  ].sort((a, b) => a.localeCompare(b));
  const shown = pass({ types, companies }).sort(
    (a, b) =>
      // The starred resume leads the list, whatever the order.
      Number(b.primary) - Number(a.primary) ||
      (sort === "name"
        ? a.name.localeCompare(b.name, undefined, { sensitivity: "base", numeric: true })
        : sort === "created"
          ? Date.parse(b.created || "0") - Date.parse(a.created || "0")
          : (Date.parse(b.at || "0") - Date.parse(a.at || "0")) * (sort === "oldest" ? -1 : 1)),
  );

  const filtered = types.length > 0 || companies.length > 0 || words.length > 0;
  function clearAll() {
    setQuery("");
    move({ types: [], companies: [] });
  }

  /** The list's rows under Type headings (Table Settings' Group By,
   *  ./resume-filters.tsx), or flat; the grid is always flat. */
  const groups =
    grid || groupBy === "none"
      ? null
      : RESUME_TYPES.map((type) => ({
          ...type,
          rows: shown.filter((row) => row.type === type.value),
        })).filter((group) => group.rows.length > 0);
  const drawRow = (row: Row) =>
    row.type === "uploaded" ? (
      <UploadedRow
        key={row.key}
        layout={shownLayout}
        resume={row.upload}
        reload={reload}
        onDelete={(send) => remove(row.key, send)}
      />
    ) : (
      <BuiltResumeRow
        key={row.key}
        layout={shownLayout}
        resume={row.built}
        reload={reload}
        onDelete={(send) => remove(row.key, send)}
      />
    );

  return (
    <>
      <ResumesHeader
        view="resumes"
        search={
          <SearchField
            id="resumes-search"
            label="Search resumes"
            placeholder="Search by name or job"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={RESUMES_SEARCH}
          />
        }
        // Generate Resume, then the layout at the right end of the search's
        // row, as the Jobs and Applications pages place their view switch.
        // Generate opens the ways to start a resume (./new-resume-dialog.tsx),
        // Upload among them: Upload Resume was a button of its own beside it
        // until 2026-11-11.
        action={
          <>
            {upload.input}
            <Button
              size="sm"
              onClick={() => setCreating(true)}
              disabled={generating !== null || upload.uploading}
            >
              <FileTextIcon aria-hidden className="size-4" />
              {generating === null ? (
                <ShortLabel verb="Generate" />
              ) : showSteps ? (
                "Generating…"
              ) : (
                "Checking…"
              )}
            </Button>
            <SegmentedToggle
              label="Layout"
              value={shownLayout}
              onValueChange={(next) => pickLayout(next as ResumesLayout)}
              options={[viewOption("list", "list"), viewOption("grid", "grid")]}
            />
          </>
        }
      />

      {/* The filter row, as the Tracker's and Up Next's (applications/
          filter-bar.tsx): the dropdowns, then at the right Clear (while
          anything is picked), All Filters and, with the list, Table
          Settings. THE DROPDOWNS STEP OUT from the right, as theirs do: Sort
          stays, about 150px, and Clear's room, All Filters and Table
          Settings take about 170px, so this row (its own @container) fits
          Type from 488px and Company from 640. */}
      <div className="mt-3 flex flex-col gap-3">
        <div className="@container flex items-center gap-2">
          <FieldFacet
            label="Type"
            Icon={TagIcon}
            options={TYPES}
            values={types}
            onChange={(values) => setTypes(values as ResumeType[])}
            className="hidden min-w-36 @min-[30.5rem]:flex"
          />
          <SearchFacet
            label="Company"
            Icon={CompanyIcon}
            searchLabel="Search companies"
            empty="No company by that name."
            options={companyOptions}
            values={companies}
            onChange={(values) => move({ companies: values })}
            className="hidden min-w-36 @min-[40rem]:flex"
          />
          <SortMenu value={sort} options={SORTS} onChange={(next) => move({ sort: next })} />
          {filtered && (
            <ClearFiltersButton
              className="animate-fade ml-auto shrink-0"
              onClick={() => {
                allButton.current?.focus();
                clearAll();
              }}
            />
          )}
          <AllFiltersButton
            ref={allButton}
            count={types.length + companies.length}
            onClick={() => setAllOpen(true)}
            className={cn("shrink-0", !filtered && "ml-auto")}
          />
          {/* The list's own control: the grid has no groups. */}
          {!grid && (
            <TableSettingsMenu>
              <GroupByOptions
                options={RESUME_GROUP_BY}
                value={groupBy}
                onChange={setResumeGroupBy}
              />
            </TableSettingsMenu>
          )}
        </div>
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        {upload.notes}
      </div>

      {rows.length === 0 && !upload.uploading ? (
        <EmptyState Icon={FileTextIcon} title="No Resumes Yet" className="mt-4">
          Upload a resume to add its experiences, or generate one from them.
        </EmptyState>
      ) : shown.length === 0 && !upload.uploading ? (
        <EmptyState
          Icon={SearchIcon}
          title="No Matching Resumes"
          className="mt-4"
          action={
            filtered && (
              <Button variant="secondary" size="sm" onClick={clearAll}>
                Clear Filters
              </Button>
            )
          }
        >
          {types.length === 1 && types[0] === "tailored" && words.length === 0
            ? "You have no tailored resumes yet. Use Tailor My Resume on a job posting's page to make one for it."
            : "None of your resumes match these filters."}
        </EmptyState>
      ) : (
        // Every resume the filters show, in the sort's order, the primary
        // first, as list cards or as the grid's (KAN-766), with no groups:
        // each card says what it is, as Google Drive's and Simplify's do.
        // Generate Resume above makes a new one; a New Resume tile first in
        // the grid did the same and came off on 2026-11-10.
        <ResumeList grid={grid}>
          {upload.pending(shownLayout)}
          {groups
            ? groups.flatMap((group) => {
                const open = !folded.has(group.value);
                return [
                  <GroupHeadingRow
                    key={`group:${group.value}`}
                    colSpan={5}
                    label={group.label}
                    count={group.rows.length}
                    open={open}
                    onToggle={() => fold(group.value)}
                    Icon={RESUME_TYPE_ICON[group.value]}
                    iconClassName="text-ink-meta"
                  />,
                  ...(open ? group.rows.map(drawRow) : []),
                ];
              })
            : shown.map(drawRow)}
        </ResumeList>
      )}
      <NewResumeDialog
        open={creating}
        onOpenChange={setCreating}
        built={resumes}
        uploaded={uploaded}
        onGenerate={() => void generate()}
        onUpload={upload.pick}
        uploadDisabled={
          upload.full
            ? `You can upload up to ${MAX_UPLOADS} resumes. Delete one to upload another.`
            : null
        }
        onCopy={copyResume}
      />
      <DuplicateResumeDialog
        duplicate={duplicate}
        onConfirm={() => {
          setDuplicate(null);
          void generate(true);
        }}
        onClose={() => setDuplicate(null)}
      />
      <GenerateRunning step={showSteps ? generating : null} />
      <ResumeAllFilters
        open={allOpen}
        onOpenChange={setAllOpen}
        picks={{ types, companies }}
        companies={companyOptions}
        count={(picks) => pass(picks).length}
        onApply={(picks) => move(picks)}
      />
    </>
  );
}
