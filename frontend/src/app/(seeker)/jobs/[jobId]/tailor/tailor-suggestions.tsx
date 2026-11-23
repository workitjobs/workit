"use client";

import type { Icon as PhosphorIcon } from "@phosphor-icons/react";
import {
  ArrowUUpLeftIcon,
  ArrowsDownUpIcon,
  CaretDownIcon,
  EyeIcon,
  EyeSlashIcon,
  MinusIcon,
  PencilSimpleIcon,
  PlusIcon,
} from "@phosphor-icons/react/ssr";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type ComponentProps } from "react";

import { facetClasses } from "@/components/field-facet";
import { ChevronDownIcon, CloseIcon, EllipsisIcon, FilterIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";
import type { Bank } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";
import type { TailorEdit } from "@/lib/tailor-actions";
import { cn } from "@/lib/cn";

import { Editor } from "../../../resumes/[resumeId]/editor";
import { wording } from "../../../resumes/[resumeId]/model";
import { ResumeTitle } from "../../../resumes/[resumeId]/resume-title";
import {
  changesOf,
  movesOf,
  useTailorReview,
  type Change,
  type ChangeKind,
  type SuggestionPopupApi,
  type SuggestionsApi,
} from "../../../resumes/[resumeId]/tailor-review";
import { OriginalResume } from "./resume-preview";
import type { JobListing } from "../../listings";
import { useTailorBack } from "./tailor-back";
import { TailorFinish, type ApplyState } from "./ready-to-apply";
import { TailorJobLine } from "./tailor-header";
import { TAILOR_STEPS } from "./tailor-steps";

/**
 * Tailor's review step (docs/tailor_resume.md, "Suggestions"), laid out as
 * a Google Doc is (KAN-499), under the step's row (`TailorReviewBar`): the
 * resume's name over its job, as a Doc's name sits over its menus, with the
 * document's actions at the row's right, the toolbar (`SlimBar`) as Docs'
 * pill, and beside the page the Suggestions panel, closed with its X as
 * Docs' comments are, or the source resume (`original`).
 * Each changed line is tinted by its type on the page, as a Doc marks a
 * suggestion in its text, with an outline while its suggestion is pointed at,
 * focused or open. A click on one opens the panel and scrolls to its
 * suggestion, outlined as its line is. A phone
 * tints only the open line and keeps a margin dot per line. Desktop had the
 * dots until the user found them apart from the words they marked.
 * The panel has a section per resume entry, top to bottom as on the page,
 * each counting its suggestions; each suggestion is a row with its type's
 * badge (added, reworded, removed, moved: a colour and a glyph) over its
 * before and after, with Undo, which reverts the change. Every change is
 * saved already, so there is nothing to accept (KAN-499). A dropdown in the
 * heading row filters by type. The editor owns the state and
 * lays the panel out (`suggestions`); this file draws it.
 *
 * The record lives in this tab's sessionStorage, so a new tab or device has
 * no suggestions: the editor shows alone, with a line that says why.
 */

/** The small card beside a clicked line (`SuggestionPopup`) is archived
 *  (2026-11-01): a click opens the panel instead, so one place holds every
 *  suggestion. To bring it back, turn this on and take `setSide` out of the
 *  editor's `onLine`, or the panel opens under the card. */
const POPUP_LIVE = false;

export function TailorReview({
  name,
  job,
  apply,
  ...editor
}: Omit<ComponentProps<typeof Editor>, "heading"> & {
  /** The tailored resume's name, the page's title. */
  name: string;
  /** The job it is tailored for, named under the title (`TailorJobLine`). */
  job: JobListing;
  /** For Finish's Your Resume Is Ready (./ready-to-apply.tsx). */
  apply: ApplyState;
}) {
  const [record] = useTailorReview(editor.resumeId);
  // Storage is read after mount; until then the page shows no line about it.
  const [read, setRead] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- marks the storage read done
    setRead(true);
  }, []);
  const noRecord = read && !record && (
    <p className="text-note text-ink-meta mt-3">
      Tailor&apos;s suggestions show only in the tab that ran Tailor.
    </p>
  );
  const back = useTailorBack(job.id, editor.resumeId);
  const step = TAILOR_STEPS.findIndex((s) => s.value === "review");
  // The phone editor covers the step's row (`TailorReviewBar`), so its
  // header carries the step and Finish (the job is under the name in its
  // title row), and its arrow goes to the step before (KAN-574).
  const phoneBar = (
    <>
      <div className="flex items-center gap-2">
        {/* The job is under the resume's name in the title row above */}
        <div className="min-w-0 flex-1">
          <p aria-current="step" className="text-note text-ink-meta truncate">
            {TAILOR_STEPS[step].label} · Step {step + 1} of {TAILOR_STEPS.length}
          </p>
        </div>
        <TailorFinish job={job} resumeId={editor.resumeId} apply={apply} />
      </div>
      {noRecord}
    </>
  );

  return (
    <>
      {noRecord}
      <Editor
        {...editor}
        heading={
          <div className="flex min-w-0 flex-col">
            <ResumeTitle resumeId={editor.resumeId} name={name} />
            <TailorJobLine job={job} />
          </div>
        }
        original={record?.source && <OriginalResume source={record.source} />}
        phoneBar={phoneBar}
        phoneBack={back}
        suggestions={SuggestionsPanel}
        suggestionPopup={POPUP_LIVE ? SuggestionPopup : undefined}
      />
    </>
  );
}

/** The number of suggestions left, as the entries' grey pill: a filled
 *  brand pill beside the rail's own brand count said it twice in two
 *  looks (2026-11-23). */
function Count({ n }: { n: number }) {
  return (
    <span className="bg-ink/5 text-ink-muted text-note flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 font-semibold tabular-nums">
      {n}
    </span>
  );
}

/**
 * Each change type's name, glyph and colours: the badge on its row and in
 * the type filter, in the colour its lines carry on the page
 * (../../../resumes/[resumeId]/pdf-pages.tsx): green added, blue reworded,
 * red removed, amber moved. A glyph as well as a colour, so the type reads
 * without telling colours apart.
 */
const KINDS: Record<ChangeKind, { label: string; Icon: PhosphorIcon; badge: string }> = {
  added: { label: "Added", Icon: PlusIcon, badge: "bg-positive-tint text-positive-ink" },
  reworded: { label: "Reworded", Icon: PencilSimpleIcon, badge: "bg-advanced-tint text-advanced" },
  removed: { label: "Removed", Icon: MinusIcon, badge: "bg-danger-tint text-danger" },
  moved: { label: "Moved", Icon: ArrowsDownUpIcon, badge: "bg-warning-tint text-warning" },
};

const KIND_ORDER: ChangeKind[] = ["added", "reworded", "removed", "moved"];

/** One section of the panel: a resume entry, or Skills, with its changes. */
type Group = { where: string; title: string; detail?: string; changes: Change[]; at: number };

/** The changes by the entry they sit in, top to bottom as on the page, and
 *  within an entry by line where the line is on the page. */
function groupsOf(changes: Change[], bank: Bank, pageOrder: (key: string) => number): Group[] {
  const lineAt = (change: Change) => {
    const edit = change.edit;
    if (edit?.kind === "reword") return pageOrder(`${edit.bullet_id}.bullet`);
    if (edit?.kind === "skill") return pageOrder(`${edit.skill_id}.skill`);
    return Number.POSITIVE_INFINITY;
  };
  const groups = new Map<string, Group>();
  for (const change of changes) {
    let group = groups.get(change.where);
    if (!group) {
      const entry = bank.entries.find((e) => e.id === change.where);
      group = entry
        ? {
            where: change.where,
            title: entry.title,
            detail: entry.organization ?? undefined,
            changes: [],
            at: pageOrder(`${entry.id}.title`),
          }
        : { where: change.where, title: "Skills", changes: [], at: Number.POSITIVE_INFINITY };
      groups.set(change.where, group);
    }
    group.changes.push(change);
  }
  for (const group of groups.values()) {
    group.changes.sort((a, b) => lineAt(a) - lineAt(b));
    if (group.where === "skills") group.at = Math.min(...group.changes.map(lineAt));
  }
  return [...groups.values()].sort((a, b) => a.at - b.at);
}

function SuggestionsPanel({
  record,
  pageOrder,
  bank,
  choices,
  undo,
  undoAll,
  close,
  focused,
  focus,
  show,
  active,
  marks,
}: SuggestionsApi) {
  const list = useRef<HTMLDivElement>(null);
  // `?sample=1` on the dev server adds a made-up change of every type the
  // run does not make yet (`sampleChanges`), to compare them all at once
  const sample = useSearchParams().get("sample") === "1" && process.env.NODE_ENV !== "production";
  const changes = [...changesOf(record.edits, bank), ...(sample ? sampleChanges(bank) : [])];
  const [only, setOnly] = useState<ChangeKind | null>(null);
  const shown = only ? changes.filter((c) => c.kind === only) : changes;
  const groups = groupsOf(shown, bank, pageOrder);
  const counts = new Map(KIND_ORDER.map((k) => [k, changes.filter((c) => c.kind === k).length]));
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  // A card opened from the page (its line or dot) opens its section, and
  // shows every type again if a filter hid it
  const [seen, setSeen] = useState(active);
  if (active !== seen) {
    setSeen(active);
    const change = changes.find((c) => c.key === active);
    if (change && closed.has(change.where)) {
      setClosed(new Set([...closed].filter((w) => w !== change.where)));
    }
    if (change && only && change.kind !== only) setOnly(null);
  }
  // The open card comes into view, by scrolling the list alone: its
  // scrollIntoView also scrolled the page, and Chrome then cancelled the
  // page's own smooth scroll to the card's lines (`focus` in PdfPages)
  useEffect(() => {
    const box = list.current;
    const card = box?.querySelector(`[data-card="${CSS.escape(active ?? "")}"]`);
    if (!active || !box || !card) return;
    const r = card.getBoundingClientRect();
    const b = box.getBoundingClientRect();
    const by =
      r.top < b.top
        ? r.top - b.top
        : r.bottom > b.bottom
          ? Math.min(r.bottom - b.bottom, r.top - b.top)
          : 0;
    if (by) box.scrollBy({ top: by, behavior: "smooth" });
  }, [active, closed]);

  const toggle = (where: string) => {
    const next = new Set(closed);
    if (next.has(where)) next.delete(where);
    else next.add(where);
    setClosed(next);
  };

  return (
    // White with the desk's outline (2026-11-23): it was the brand tint,
    // the colour every picked control wears, so the whole panel read as
    // picked and a third material beside the desk's grey and the page's
    // white. Bare in the phone's sheet, which is its own panel
    <section
      aria-labelledby="suggestions-heading"
      className="sm:bg-panel sm:ring-border-surface sm:rounded-card flex min-h-0 flex-col sm:ring-1"
    >
      {/* The top stays put and only the entries under it scroll, so the
          scroll bar starts under it and the panel keeps its rounded corners.
          Two rows (2026-11-23): the title and its close, then what acts on
          the list, the filter and a ⋯ with words. Six controls on one row,
          four of them bare icons and Undo All drawn as each card's Undo,
          read as clutter, and the one that undoes everything looked like
          the one that undoes one */}
      <div className="border-border-subtle flex shrink-0 flex-col gap-2 border-b px-3 pt-3 pb-2.5 max-sm:px-0 max-sm:pt-0">
        <div className="flex min-h-8 items-center gap-2">
          <h2
            id="suggestions-heading"
            className="text-subtitle text-ink mr-auto flex items-center gap-2 font-semibold max-sm:sr-only"
          >
            Suggestions <Count n={changes.length} />
          </h2>
          {/* A phone's sheet has its own X */}
          <IconButton
            place="row"
            label="Close Suggestions"
            tooltip={false}
            className="shrink-0 max-sm:hidden"
            onClick={close}
          >
            <CloseIcon />
          </IconButton>
        </div>
        {changes.length > 0 && (
          <div className="flex items-center gap-2">
            <TypeFilter only={only} counts={counts} onChange={setOnly} />
            <ListMenu marks={marks} undoAll={undoAll} />
          </div>
        )}
      </div>
      {changes.length > 0 ? (
        // relative: each row's sr-only label is absolute, and with no
        // positioned box here the list did not clip it, so the labels of
        // rows past its fold stretched the page's scroll (KAN-499)
        <div
          ref={list}
          className="divide-border-subtle relative flex min-h-0 flex-col divide-y overflow-y-auto overscroll-none"
        >
          {groups.map((group) => {
            const isOpen = !closed.has(group.where);
            return (
              // One section per resume entry, as the page lists them, under
              // a hairline, with no box of its own (2026-11-23): a white box
              // per entry, a box per change inside it and the panel round
              // them were three frames deep, and the entries' outlines, drawn
              // outside their boxes, were cut off by the list's edge
              <section
                key={group.where}
                aria-label={group.title}
                // shrink-0: in the scrolling list a clipped section would
                // otherwise squeeze to fit rather than scroll
                className="shrink-0 px-1.5 py-1.5 max-sm:px-0"
              >
                <h3>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => toggle(group.where)}
                    className="hover:bg-ink/[0.03] focus-visible:outline-brand rounded-control flex w-full items-center gap-2 px-1.5 py-2 text-left -outline-offset-2 transition-colors focus-visible:outline-2"
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="text-label text-ink truncate font-semibold">
                        {group.title}
                      </span>
                      {group.detail && (
                        <span className="text-note text-ink-meta truncate">{group.detail}</span>
                      )}
                    </span>
                    <span className="bg-ink/5 text-ink-muted text-note flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1.5 font-semibold tabular-nums">
                      {group.changes.length}
                    </span>
                    <Chevron open={isOpen} />
                  </button>
                </h3>
                {isOpen && (
                  <ul role="list" className="flex flex-col gap-0.5">
                    {group.changes.map((change) => (
                      <li key={change.key}>
                        <Suggestion
                          change={change}
                          bank={bank}
                          choices={choices}
                          lit={focused === change.key}
                          current={active === change.key}
                          onFocus={focus}
                          onShow={() => show(change.key)}
                          onUndo={() => !isSample(change) && undo(change.edit)}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            );
          })}
        </div>
      ) : (
        <p className="text-note text-ink-meta px-3 py-3 max-sm:px-0">
          No suggestions left. Edit anything else on the resume.
        </p>
      )}
    </section>
  );
}

/**
 * What acts on the whole list, in a ⋯ at the filter's row, each in words:
 * the marks on the page, and Undo All Suggestions, last and red, as every
 * menu's delete is. They were two bare icons in the title's row, and Undo
 * All wore each card's Undo arrow (2026-11-23).
 */
function ListMenu({ marks, undoAll }: { marks: SuggestionsApi["marks"]; undoAll: () => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <IconButton
            place="row"
            label="More for Suggestions"
            tooltip={false}
            className="ml-auto shrink-0"
          >
            <EllipsisIcon />
          </IconButton>
        }
      />
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuItem onClick={marks.onToggle}>
          {marks.shown ? <EyeSlashIcon aria-hidden /> : <EyeIcon aria-hidden />}
          {marks.shown ? "Hide Marks on the Page" : "Show Marks on the Page"}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onClick={undoAll}>
          <ArrowUUpLeftIcon aria-hidden />
          Undo All Suggestions
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * The change types as a filter dropdown in the panel's heading row, drawn
 * as the Resumes page's Type filter is (`facetClasses`, brand-tinted while
 * it holds a pick). Its button names the type shown, with that type's
 * badge; its menu lists All Types and each type present, with its badge
 * and count. The types were a two-by-two legend of coloured pills under
 * the keyword match until 2026-10-26, which took four rows' height.
 */
function TypeFilter({
  only,
  counts,
  onChange,
}: {
  only: ChangeKind | null;
  counts: Map<ChangeKind, number>;
  onChange: (only: ChangeKind | null) => void;
}) {
  const total = [...counts.values()].reduce((sum, n) => sum + n, 0);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Show ${only ? KINDS[only].label : "All Types"}`}
        className={facetClasses(only !== null, "gap-1.5 px-2.5")}
      >
        <span className="flex min-w-0 items-center gap-1.5">
          {only ? (
            <KindBadge kind={only} small />
          ) : (
            <FilterIcon className="text-ink-meta size-4 shrink-0" />
          )}
          <span className="truncate">{only ? KINDS[only].label : "All Types"}</span>
        </span>
        <ChevronDownIcon className="text-ink-meta size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuRadioGroup
          value={only ?? "all"}
          onValueChange={(next) => onChange(next === "all" ? null : (next as ChangeKind))}
        >
          <DropdownMenuRadioItem value="all" className="gap-2">
            <FilterIcon className="text-ink-meta size-4" />
            All Types
            <span className="text-ink-meta ml-auto tabular-nums">{total}</span>
          </DropdownMenuRadioItem>
          {KIND_ORDER.filter((k) => counts.get(k)).map((k) => (
            <DropdownMenuRadioItem key={k} value={k} className="gap-2">
              <KindBadge kind={k} small />
              {KINDS[k].label}
              <span className="text-ink-meta ml-auto tabular-nums">{counts.get(k)}</span>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** A section's sign that it folds: a caret at its heading's end, turned
 *  up while open. */
function Chevron({ open }: { open: boolean }) {
  return (
    <CaretDownIcon
      aria-hidden
      className={cn(
        "text-ink-meta ml-auto size-4 shrink-0 transition-transform duration-150",
        open && "rotate-180",
      )}
    />
  );
}

/** A row's type, as a small round badge in its colour with its glyph. */
function KindBadge({ kind, small = false }: { kind: ChangeKind; small?: boolean }) {
  const { Icon, badge } = KINDS[kind];
  return (
    <span
      aria-hidden
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full",
        small ? "size-5" : "size-6",
        badge,
      )}
    >
      <Icon weight="bold" className={small ? "size-3" : "size-3.5"} />
    </span>
  );
}

/**
 * One suggestion, a row in its entry's section, always open: its type's
 * badge and name, Undo at its end, and under them the change (`ChangeBody`).
 * Accept and Reject sat there until KAN-499: the change is saved already,
 * so Accept did nothing to the resume. A click on it
 * shows its lines on the page (`onShow`: highlighted and scrolled to; on a
 * phone the sheet closes); pointing at it highlights them without
 * scrolling. Each row folded on its own, with a plus and a minus, until
 * 2026-10-26: a fold inside a folding section read as nested and odd, so
 * only sections fold. Sections were by type (Reworded Bullets, Reordered
 * Bullets, Added Skills) before that: with every type in play, a student
 * reads the panel against the page, so sections follow the page and the
 * type is each row's badge.
 */
function Suggestion({
  change,
  bank,
  choices,
  lit,
  current,
  onFocus,
  onShow,
  onUndo,
}: {
  change: Change;
  bank: Bank;
  choices: Choices;
  /** Pointed at or focused. */
  lit: boolean;
  /** Last shown on the page, from here or from its line or dot there. */
  current: boolean;
  onFocus: (key: string | null) => void;
  onShow: () => void;
  onUndo: () => void;
}) {
  return (
    <div
      data-card={change.key}
      onMouseEnter={() => onFocus(change.key)}
      onMouseLeave={() => onFocus(null)}
      onFocus={() => onFocus(change.key)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) onFocus(null);
      }}
      // Grey while pointed at or shown on the page, never brand: a row in
      // purple read as selected for something else. The one shown on the page
      // is also outlined as its lines are, so a click on a line lands on a
      // row that is plain to see among the others. Its badge sits on the
      // entry title's edge, and its name and change on one edge after it
      // (2026-11-23): three left edges made the column ragged
      className={cn(
        "rounded-control flex scroll-mt-2 items-start gap-2.5 px-1.5 py-2 transition-[background-color,box-shadow]",
        (lit || current) && "bg-ink/[0.03]",
        current && "ring-ink/25 ring-1 ring-inset",
      )}
    >
      <KindBadge kind={change.kind} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start gap-1">
          <button
            type="button"
            onClick={onShow}
            className="text-note text-ink focus-visible:outline-brand flex min-h-6 min-w-0 flex-1 items-center rounded-xs text-left font-semibold focus-visible:outline-2"
          >
            {title(change)}
            <span className="sr-only">, show on the resume</span>
          </button>
          <IconButton
            place="row"
            label="Undo This Change"
            tooltip="Undo This Change"
            className="-my-1.5 shrink-0"
            onClick={onUndo}
          >
            <ArrowUUpLeftIcon aria-hidden />
          </IconButton>
        </div>
        <ChangeBody change={change} bank={bank} choices={choices} />
      </div>
    </div>
  );
}

/** A changed line's card beside the line: what changed, and Undo, as Docs
 *  answers a suggestion beside its text. It says the same as the panel's
 *  row, so a student can settle one change with the panel closed. */
function SuggestionPopup({ edit, bank, choices, undo, close }: SuggestionPopupApi) {
  const change = changesOf([edit], bank)[0];
  return (
    <div className="flex flex-col gap-2 p-3">
      <div className="flex items-center gap-2">
        <KindBadge kind={change.kind} small />
        <span className="text-note text-ink min-w-0 flex-1 truncate font-semibold">
          {title(change)}
        </span>
        <IconButton
          place="row"
          label={`Undo: ${title(change)}`}
          tooltip={false}
          className="shrink-0"
          onClick={undo}
        >
          <ArrowUUpLeftIcon aria-hidden />
        </IconButton>
        <IconButton place="row" tooltip={false} label="Close" className="shrink-0" onClick={close}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="max-h-48 overflow-y-auto overscroll-none">
        <ChangeBody change={change} bank={bank} choices={choices} />
      </div>
    </div>
  );
}

/** A row's name for its change: "Reworded bullet", "Added skill ·
 *  Languages". */
function title(change: Change) {
  if (change.kind === "moved") return "Bullets moved";
  const name = `${KINDS[change.kind].label} ${change.where === "skills" ? "skill" : "bullet"}`;
  return change.group ? `${name} · ${change.group}` : name;
}

/**
 * A change under its row's name, with no box (2026-11-23): an added skill
 * as a chip, as the Edit Skill Group dialog draws one; an added or removed
 * line in plain type; each moved bullet with its place before and after as
 * an amber tag; a rewording as Was over Now (`wordChanges`). A white card
 * with an outline held each change until then, a third frame inside the
 * panel and its entry, and a rewording showed its whole old line struck in
 * red over its whole new line in green: struck paragraphs are hard to read,
 * a line all marked marks nothing, and green is the added colour, not the
 * reworded one. Its new words alone in green, with Show Before, came next
 * for a day.
 */
function ChangeBody({ change, bank, choices }: { change: Change; bank: Bank; choices: Choices }) {
  if (change.kind === "added" && change.where === "skills")
    return (
      <span className="bg-positive-tint text-positive-ink text-note rounded-control self-start px-2 py-0.5 font-medium">
        {change.after}
      </span>
    );
  if (change.kind === "added") return <p className="text-note text-ink">{change.after}</p>;
  if (change.kind === "removed") return <p className="text-note text-ink-meta">{change.before}</p>;
  if (change.kind === "moved" && change.edit) {
    const entryId = change.edit.entry_id;
    const bullets = bank.entries.find((e) => e.id === entryId)?.bullets ?? [];
    return (
      <ul role="list" className="flex flex-col gap-1.5">
        {movesOf(change.edit, choices).map(({ bulletId, from, to }) => {
          const bullet = bullets.find((b) => b.id === bulletId);
          return (
            <li key={bulletId} className="text-note text-ink flex items-start gap-2">
              <span className="bg-warning-tint text-warning rounded-md px-1.5 py-px font-semibold whitespace-nowrap tabular-nums">
                <span className="sr-only">
                  From {ordinal(from)} to {ordinal(to)}:{" "}
                </span>
                <span aria-hidden>
                  {from} → {to}
                </span>
              </span>
              <span className="line-clamp-2 min-w-0 flex-1">
                {bullet ? wording(choices, bullet) : ""}
              </span>
            </li>
          );
        })}
      </ul>
    );
  }
  const after = change.after ?? "";
  const old = change.before;
  if (!old) return <p className="text-note text-ink">{after}</p>;
  // Was over Now, both always shown (2026-11-23, the user's pick of three):
  // the student keeps or undoes it by comparing the two, so the old words
  // were one click away behind Show Before. A few words changed: the gone
  // ones struck in grey, the new ones in the reworded blue, as the page
  // tints the line. Most of the line changed, as an AI rewording mostly
  // does: no marks, since a line all marked marks nothing
  const words = wordChanges(old, after);
  const marked = words.share <= 0.5;
  return (
    <dl className="text-note grid grid-cols-[auto_minmax(0,1fr)] gap-x-2.5 gap-y-1.5">
      <dt className={PAIR_LABEL}>Was</dt>
      <dd className="text-ink-meta">
        {words.old.map((run, i) =>
          marked && run.changed ? (
            <del key={i} className="decoration-ink-meta/70 line-through">
              {run.text}
            </del>
          ) : (
            <span key={i}>{run.text}</span>
          ),
        )}
      </dd>
      <dt className={PAIR_LABEL}>Now</dt>
      <dd className="text-ink">
        {words.now.map((run, i) =>
          marked && run.changed ? (
            <ins
              key={i}
              className="bg-advanced-tint rounded-sm box-decoration-clone px-0.5 no-underline"
            >
              {run.text}
            </ins>
          ) : (
            <span key={i}>{run.text}</span>
          ),
        )}
      </dd>
    </dl>
  );
}

/** "Was" and "Now" before a rewording's two lines: small, quiet labels on
 *  the lines' first baselines. */
const PAIR_LABEL = "text-caption text-ink-meta pt-px font-semibold uppercase tracking-wide";

function ordinal(n: number) {
  const tens = n % 100;
  const suffix = tens >= 11 && tens <= 13 ? "th" : (["th", "st", "nd", "rd"][n % 10] ?? "th");
  return `${n}${suffix}`;
}

/** A word as two lines compare it: its letters, numbers and the symbols
 *  that change what it says ("C++", "50%"), in any case. */
const keyOf = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}+#%$]/gu, "");

type Run = { text: string; changed: boolean };

/** Words with the spaces between them kept, and each word's key. */
function wordsOf(line: string) {
  const parts = line.trim().split(/(\s+)/);
  const words = parts.filter((_, i) => i % 2 === 0);
  return { parts, words, keys: words.map(keyOf) };
}

/** Words as runs, a run per stretch of changed or kept words. The space
 *  between two runs goes with the kept one, so a mark ends at its word: it
 *  ran on over the next space (2026-11-23). A word with no letters or
 *  numbers (a dash) follows its neighbour. */
function runsOf({ parts, words, keys }: ReturnType<typeof wordsOf>, changed: boolean[]): Run[] {
  words.forEach((_, j) => {
    if (!keys[j] && j > 0) changed[j] = changed[j - 1];
  });
  const runs: Run[] = [];
  words.forEach((word, j) => {
    const space = j > 0 ? parts[2 * j - 1] : "";
    const last = runs.at(-1);
    if (last && last.changed === changed[j]) last.text += space + word;
    else if (last && !last.changed) {
      last.text += space;
      runs.push({ text: word, changed: changed[j] });
    } else runs.push({ text: space + word, changed: changed[j] });
  });
  return runs;
}

/**
 * A rewording's two lines as runs of words, each marked where the other
 * line does not have it in that order (a longest common run of words,
 * compared by `keyOf`), and the share of the new line's words that are new.
 * A head-and-tail match came first: it marked a whole line whenever a word
 * near its start changed.
 */
export function wordChanges(before: string, after: string) {
  const was = wordsOf(before);
  const now = wordsOf(after);
  const a = was.keys;
  const b = now.keys;
  // lcs[i][j]: the longest common run of a[i..] and b[j..]
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      lcs[i][j] =
        a[i] && a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  const gone = new Array<boolean>(a.length).fill(true);
  const added = new Array<boolean>(b.length).fill(true);
  for (let i = 0, j = 0; i < a.length && j < b.length;) {
    if (a[i] && a[i] === b[j]) {
      gone[i] = false;
      added[j] = false;
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) i++;
    else j++;
  }
  const share = b.length ? added.filter(Boolean).length / b.length : 0;
  return { old: runsOf(was, gone), now: runsOf(now, added), share };
}

/** A made-up change, `sampleChanges`': its Undo does nothing. */
const isSample = (change: Change) => change.key.startsWith("sample:");

/**
 * Made-up changes for the dev server's `?sample=1` (2026-11-23), drawn from
 * the resume's own entries, of each type the run does not make yet: an
 * added bullet, a removed bullet, a rewording of most of a line (shown with
 * no marks), and a removed and an added skill. The panel was first drawn
 * against sample changes too (docs/tailor_resume.md, "Added bullets and
 * removed lines are drawn but not yet made"). Never in production, and
 * never on the page or in the record: nothing here is saved or undone.
 */
function sampleChanges(bank: Bank): Change[] {
  const entries = bank.entries.filter((e) => e.section !== "education" && e.bullets.length > 1);
  const [first, second] = [entries[0], entries[1] ?? entries[0]];
  if (!first) return [];
  const edit = { kind: "skill", skill_id: "sample" } as TailorEdit;
  const skill = bank.skills[0];
  return [
    {
      key: "sample:added-bullet",
      kind: "added",
      where: first.id,
      edit,
      after: "Ran weekly design reviews with two engineers, cutting rework on shipped screens.",
    },
    {
      key: "sample:removed-bullet",
      kind: "removed",
      where: first.id,
      edit,
      before: first.bullets.at(-1)?.text,
    },
    {
      key: "sample:rewrite",
      kind: "reworded",
      where: second.id,
      edit,
      before: second.bullets[0]?.text,
      after: "Shipped a design system of 40 components that four teams adopted within one term.",
    },
    {
      key: "sample:removed-skill",
      kind: "removed",
      where: "skills",
      edit,
      before: skill?.name ?? "Jira",
      group: skill?.group ?? undefined,
    },
    {
      key: "sample:added-skill",
      kind: "added",
      where: "skills",
      edit,
      after: "GraphQL",
      group: "Engineering",
    },
  ];
}
