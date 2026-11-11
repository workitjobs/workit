"use client";

import {
  ArrowCounterClockwiseIcon,
  ArrowDownIcon,
  ArrowsInLineVerticalIcon,
  ArrowUUpLeftIcon,
  ArrowUUpRightIcon,
  ArrowUpIcon,
  CircleNotchIcon,
  EyeSlashIcon,
  IdentificationCardIcon,
  LightbulbIcon,
  PencilSimpleIcon,
  ScissorsIcon,
  SidebarSimpleIcon,
  StackIcon,
  TextBIcon,
  TextItalicIcon,
} from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
  type RefObject,
} from "react";

import { CheckIcon, EllipsisIcon, FileIcon, PlusIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Skeleton } from "@/components/shadcn/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/shadcn/tooltip";
import { Button, buttonClasses } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Tip } from "@/components/ui/tip";
import type {
  Choices,
  ChoicesUpdate,
  PageSettings,
  RenderBox,
  RenderedPdf,
} from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

import { FOLD, FoldButton } from "./bar-fold";
import { typed, type Line } from "./model";
import { degreeLeads, ON, SizeStepper, TEXT_ROLES, textRoleOf, type TextRole } from "./page-format";
import { SLIM_BAR } from "./slim-bar";
import { unmarked } from "./text-marks";
import { Zoom, ZoomSubmenu } from "./zoom";

/** The editor's Undo and Redo (./history.ts), for the slim bar and the
 *  phone's bar. */
export type HistoryTools = {
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
};

/** Move Up and Move Down for the open line: a bullet within its entry, an
 *  entry within its section. */
export type MoveTools = { up: boolean; down: boolean; onMove: (by: -1 | 1) => void };

/** The toolbar's Experiences (KAN-440): whether Scout's panel shows the
 *  picker now. */
export type ExperiencesTools = {
  /** Add Experiences, on the editor's own page only. */
  picker: { open: boolean; onToggle: () => void } | null;
  /** Cut From Resume, only after a fit cut something still off the page. */
  cut: { open: boolean; onToggle: () => void } | null;
};

/** The page's zoom and its setter (./zoom.tsx), for the bar's `Zoom` and
 *  More's `ZoomSubmenu`. */
export type ZoomTools = { zoom: number; onZoom: (zoom: number) => void };

/** The bar's page settings (./page-format.tsx). */
export type FormatTools = {
  page: PageSettings;
  disabled: boolean;
  onChange: (next: PageSettings) => void;
  /** Whether the side panel is open, and its button (KAN-586): the panel
   *  holds Sections and Format as tabs, so neither has a button of its own. */
  panelOpen: boolean;
  onPanel: () => void;
};

/** The side panel's tabs (KAN-586). */
export type PanelTab = "sections" | "format";

/** What sits beside the page on Tailor's review. */
export type Side = "suggestions" | "original" | PanelTab | "cut" | null;

/** The title row's review tools: the changes left, and which column shows
 *  beside the page. */
export type ReviewTools = {
  count: number;
  side: Side;
  onSide: (side: Side) => void;
  /** False when the run's record names no source resume. */
  hasOriginal: boolean;
};

/**
 * Whether the edits are saved, in the title row beside Download on the
 * desktop and at the end of the phone's top row (KAN-799): "Saving…" while
 * anything is on its way, "Saved" once the first render has landed and
 * nothing is. It read "Saved, N ms", the render's time, which was for us,
 * not for a student, and it sat in the bar and left it below 58rem. An
 * error is not said here: the line under the bar says what went wrong.
 */
export function SaveStatus({
  saving,
  fitting,
  ready,
  short = false,
}: {
  saving: boolean;
  fitting: boolean;
  /** The first render has landed. */
  ready: boolean;
  /** The phone's "Fitting…", for its narrow row. */
  short?: boolean;
}) {
  const saved = ready && !saving && !fitting;
  return (
    <span
      aria-live="polite"
      className="text-note text-ink-meta flex shrink-0 items-center gap-1 whitespace-nowrap"
    >
      {saved && <CheckIcon className="size-3.5" />}
      {fitting
        ? short
          ? "Fitting…"
          : "Fitting to One Page…"
        : saving
          ? "Saving…"
          : saved
            ? "Saved"
            : ""}
    </span>
  );
}

/**
 * One of an open line's tools after its size and its bold and italic: what
 * the desktop bar draws in its middle group and lists in More once it has
 * left a narrow bar, and what the phone's line sheet draws (KAN-799), so both
 * layouts offer the same tools in the same order. The desktop had no Hide or
 * Original for a bullet and no Hide for a skill until then, and the phone had
 * no Add Bullet.
 */
export type LineTool = {
  /** Its `data-fold` box, which More reads. */
  key: string;
  label: string;
  icon?: ReactNode;
  /** A ghost glyph with no word (Move Up, Move Down); otherwise a secondary
   *  button with its word. */
  glyph?: boolean;
  /** What a tooltip adds to the name. */
  hint?: string;
  /** A link, not an action. */
  href?: string;
  disabled?: boolean;
  onClick?: () => void;
  /** When it leaves a narrow bar for More (`FOLD.line`): the least needed
   *  first, then the moves, then the line's main tools. */
  leaves: "extra" | "move" | "main";
};

/** What the open line's tools act through, from the editor. */
export type LineHandlers = {
  /** The open bullet's or entry's Move Up and Move Down; null for any other
   *  line. */
  moves: MoveTools | null;
  onApply: (changes: ChoicesUpdate) => void;
  /** Applies a hide and closes the line, which has left the page. */
  onHide: (changes: ChoicesUpdate) => void;
  onAddBullet: () => void;
  /** Opens the outline's Header row, from a line of the header. */
  onOpenHeader: () => void;
};

/**
 * The open line's tools, in order (KAN-799): a bullet's Move Up and Move
 * Down, Add Bullet, Hide and, while it shows another wording, Original; an
 * entry's moves, Add Bullet, Hide Entry, Education's GPA and Coursework, and
 * Edit in Experiences for a field the page cannot type; the header's Edit
 * Header; a skill's Hide. `onHide` also closes the line, which has left the
 * page.
 */
export function lineTools(
  line: Line,
  choices: Choices,
  { moves, onApply, onHide, onAddBullet, onOpenHeader }: LineHandlers,
): LineTool[] {
  if (line.kind === "header") {
    // Every header field, and whether this resume prints it, is in the
    // Header panel (KAN-436): a field the profile lacks, or one this resume
    // hides, has no line to click
    return [
      {
        key: "header",
        label: "Edit Header",
        icon: <IdentificationCardIcon aria-hidden />,
        hint:
          line.field === "email"
            ? "Your email is set on My Profile, so it changes on every resume"
            : undefined,
        onClick: onOpenHeader,
        leaves: "main",
      },
    ];
  }
  if (line.kind === "skill") {
    return [
      {
        key: "hide",
        label: "Hide",
        icon: <EyeSlashIcon aria-hidden />,
        hint: "Take this skill off this resume",
        onClick: () => onHide({ skills: [{ skill_id: line.skill.id, shown: false }] }),
        leaves: "main",
      },
    ];
  }
  const tools: LineTool[] = [];
  if (moves) {
    tools.push(
      {
        key: "move-up",
        label: "Move Up",
        icon: <ArrowUpIcon aria-hidden />,
        glyph: true,
        disabled: !moves.up,
        onClick: () => moves.onMove(-1),
        leaves: "move",
      },
      {
        key: "move-down",
        label: "Move Down",
        icon: <ArrowDownIcon aria-hidden />,
        glyph: true,
        disabled: !moves.down,
        onClick: () => moves.onMove(1),
        leaves: "move",
      },
    );
  }
  tools.push({
    key: "add-bullet",
    label: "Add Bullet",
    icon: <PlusIcon />,
    onClick: onAddBullet,
    leaves: "main",
  });
  if (line.kind === "bullet") {
    const id = line.bullet.id;
    const row = choices.bullets.find((c) => c.bullet_id === id);
    // One wording button, Original, shown while the bullet shows any other
    // wording (Tailor's or one typed on this resume): it puts the bank's
    // text back, and Undo takes it back. The resume's own wording stays
    // stored. A "Tailored N" button per Tailor wording went first, then a
    // This Resume's Wording button; the user wanted Original alone
    // (2026-10-29)
    const reworded = row?.variant_id != null || row?.text != null;
    tools.push({
      key: "hide",
      label: "Hide",
      icon: <EyeSlashIcon aria-hidden />,
      hint: "Take this bullet off this resume",
      onClick: () => onHide({ bullets: [{ bullet_id: id, shown: false }] }),
      leaves: "main",
    });
    if (reworded) {
      tools.push({
        key: "original",
        label: "Original",
        icon: <ArrowCounterClockwiseIcon aria-hidden />,
        hint: `Back to the wording in Experiences: ${unmarked(line.bullet.text)}`,
        onClick: () => onApply({ bullets: [{ bullet_id: id, variant_id: null }] }),
        leaves: "extra",
      });
    }
    return tools;
  }
  const entry = line.entry;
  const choice = choices.entries.find((c) => c.entry_id === entry.id);
  tools.push({
    key: "hide",
    label: "Hide Entry",
    icon: <EyeSlashIcon aria-hidden />,
    hint: "Take this entry off this resume",
    onClick: () => onHide({ entries: [{ entry_id: entry.id, shown: false }] }),
    leaves: "main",
  });
  if (entry.section === "education" && choice) {
    tools.push(
      {
        key: "gpa",
        label: choice.show_gpa ? "Hide GPA" : "Show GPA",
        onClick: () => onApply({ entries: [{ entry_id: entry.id, show_gpa: !choice.show_gpa }] }),
        leaves: "extra",
      },
      {
        key: "coursework",
        label: choice.show_coursework ? "Hide Coursework" : "Show Coursework",
        onClick: () =>
          onApply({
            entries: [{ entry_id: entry.id, show_coursework: !choice.show_coursework }],
          }),
        leaves: "extra",
      },
    );
  }
  if (!typed(line)) {
    // A button, not a sentence among the buttons: "Change this in
    // Experiences." sat in the bar as text until KAN-799
    tools.push({
      key: "experiences",
      label: "Edit in Experiences",
      icon: <PencilSimpleIcon aria-hidden />,
      hint: "This field is not typed on the page",
      href: "/experiences",
      leaves: "extra",
    });
  }
  return tools;
}

/** A tool as the phone's line sheet draws it: the bar's own weights, a ghost
 *  glyph for a move and a secondary button with its word for the rest. */
export function SheetTool({ tool }: { tool: LineTool }) {
  if (tool.href) {
    return (
      <Link href={tool.href} className={buttonClasses({ variant: "secondary", size: "sm" })}>
        {tool.icon} {tool.label}
      </Link>
    );
  }
  if (tool.glyph) {
    return (
      <Tip label={tool.label}>
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label={tool.label}
          disabled={tool.disabled}
          onClick={tool.onClick}
        >
          {tool.icon}
        </Button>
      </Tip>
    );
  }
  return (
    <Button variant="secondary" size="sm" disabled={tool.disabled} onClick={tool.onClick}>
      {tool.icon} {tool.label}
    </Button>
  );
}

/** The bar above the page's state while a line is open: its kind of text,
 *  whether it takes bold and italic, its tools and the way out. */
export type OpenLine = {
  role: TextRole;
  marks: boolean;
  tools: LineTool[];
  /** Done: saves the line and closes it, as Esc does. */
  onDone: () => void;
};

/** The open line as the bar shows it, or null while no line is open. A
 *  bullet being added (`composing`) has its size, bold, italic and Done. */
export function openLineOf({
  line,
  box,
  composing,
  page,
  tools,
  onDone,
}: {
  line: Line | null;
  box: RenderBox | undefined;
  composing: boolean;
  page: PageSettings;
  tools: LineTool[];
  onDone: () => void;
}): OpenLine | null {
  if (composing) return { role: TEXT_ROLES.body, marks: true, tools: [], onDone };
  if (!line || !box) return null;
  return {
    // The size names its kind of text: an unnamed size looked as if it
    // changed the selection, and it changes every line of that kind
    role: textRoleOf(
      box.kind,
      "entry" in line ? line.entry.section : null,
      "entry" in line && degreeLeads(line.entry, page),
    ),
    marks: line.kind === "bullet",
    tools,
    onDone,
  };
}

/** A thin rule between the bar's groups. */
const Divider = () => <span aria-hidden className="bg-border-subtle mx-1 h-5 w-px shrink-0" />;

/**
 * The slim bar over the page (KAN-411, KAN-799), the editor's one toolbar, on
 * its own page and on Tailor's review, in one shape (`SLIM_BAR`; Tailor's had
 * a pill of its own, `DOCS_BAR`, until KAN-799). It holds editing tools only,
 * in three groups that keep their places:
 *
 *   Undo Redo | <the middle> ........ Sections  Format Options | Zoom  (More)
 *
 * The middle is the page's tools while no line is open (Add Experiences, on
 * the editor's own page; Fit to One Page, over one page only; Cut From
 * Resume, after a fit cut something), and the open line's tools while one
 * is (its size, a bullet's bold and italic, `lineTools`, then Done). Only the
 * middle changes when a line opens: until KAN-799 the panels, the zoom,
 * Download and More left the bar, Fit moved, and "Esc when done" stood as
 * text where Done now is (Esc still closes the line). Download and the save
 * status are the file's, in the title row above, not tools.
 *
 * One row at every width, idle and with any line open: it folds by measure
 * (`useFoldToFit`, ./bar-fold.tsx), words first, then whole controls into
 * More. No "Click a line to edit it." hint: the
 * pointer's own highlight on a line says so. No Ask Scout: the top bar's
 * Scout opens the assistant (`ScoutTakeover`), and a second AI entry here
 * split the page's attention.
 */
export function Bar({
  line,
  box,
  choices,
  handlers,
  onDone,
  rendered,
  saving,
  fitting,
  composing,
  onFit,
  experiences,
  format,
  zoom,
  history,
}: {
  /** The open line and its box, or null while none is. */
  line: Line | null;
  box: RenderBox | undefined;
  choices: Choices;
  handlers: LineHandlers;
  /** Done: saves the line and closes it, as Esc does; a bullet being added
   *  is added, or dropped while empty. */
  onDone: () => void;
  /** Null until the first render lands. */
  rendered: RenderedPdf | null;
  saving: boolean;
  /** A Fit to One Page is under way. */
  fitting: boolean;
  /** A bullet is being added: Fit would read a resume without it. */
  composing: boolean;
  onFit: () => void;
  experiences: ExperiencesTools | null;
  format: FormatTools;
  zoom: ZoomTools;
  history: HistoryTools;
}) {
  const open = openLineOf({
    line,
    box,
    composing,
    page: format.page,
    tools: line ? lineTools(line, choices, handlers) : [],
    onDone,
  });
  const bar = useRef<HTMLDivElement>(null);
  const fits = !composing && rendered && rendered.page_count > 1;
  // The fold measures again whenever what the row holds changes
  useFoldToFit(
    bar,
    open
      ? [
          "line",
          open.role.label,
          open.marks,
          ...open.tools.map((t) => `${t.key}:${t.label}`),
          Boolean(rendered),
        ].join("|")
      : [
          "idle",
          Boolean(experiences?.picker),
          Boolean(experiences?.cut),
          fits && (fitting ? "fitting" : "fit"),
          Boolean(rendered),
        ].join("|"),
  );
  // Each piece that can leave the row sits in a `data-fold` box, which More
  // reads, with the step that folds it (./bar-fold.tsx)
  const steps = open ? FOLD.line : null;
  return (
    <div
      ref={bar}
      data-keeps-selection
      data-page-bar
      className={cn(SLIM_BAR, "@container/bar")}
      // A press on a button keeps focus in the open line's field, so it does
      // not blur and save first
      onMouseDown={(e) => {
        if (open && (e.target as HTMLElement).closest("button")) e.preventDefault();
      }}
    >
      <History tools={history} />
      <Divider />
      {open ? (
        <LineGroup open={open} format={format} />
      ) : (
        <>
          {experiences?.picker && (
            // Tinted while its panel is open
            <span
              data-fold="experiences"
              data-away-at={FOLD.idle.experiencesAt}
              data-word-at={FOLD.idle.experiencesWordAt}
              className={cn("flex shrink-0", FOLD.away)}
            >
              <FoldButton
                label="Add Experiences"
                hint="Pick what this resume shows"
                icon={<StackIcon aria-hidden />}
                fold={FOLD.word}
                render={
                  <Button
                    variant="secondary"
                    size="sm"
                    aria-pressed={experiences.picker.open}
                    className={cn(
                      experiences.picker.open &&
                        "border-brand bg-brand-tint text-brand hover:bg-brand-tint",
                    )}
                    onClick={experiences.picker.onToggle}
                  />
                }
              />
            </span>
          )}
          {fits && (
            // Its word folds late, and it never leaves the row
            <span data-word-at={FOLD.idle.fitWordAt} className="flex shrink-0">
              <FitButton
                pages={rendered.page_count}
                linesOver={rendered.lines_over}
                disabled={saving}
                fitting={fitting}
                onFit={onFit}
              />
            </span>
          )}
          {experiences?.cut && (
            // Beside Fit, in the same weight, amber as the page count is
            <span
              data-fold="cut"
              data-away-at={FOLD.idle.cutAt}
              data-word-at={FOLD.idle.cutWordAt}
              className={cn("flex shrink-0", FOLD.away)}
            >
              <FoldButton
                label="Cut From Resume"
                hint="Put back what Fit to One Page cut"
                icon={<ScissorsIcon aria-hidden />}
                fold={FOLD.word}
                render={
                  <Button
                    variant="secondary"
                    size="sm"
                    aria-pressed={experiences.cut.open}
                    className={cn(
                      "text-warning hover:text-warning",
                      experiences.cut.open &&
                        "border-warning/50 bg-warning-tint hover:bg-warning-tint",
                    )}
                    onClick={experiences.cut.onToggle}
                  />
                }
              />
            </span>
          )}
        </>
      )}
      <div className="ml-auto flex shrink-0 items-center gap-2">
        {/* Until the first render lands, the zoom is a bar, not its
            numbers in grey (KAN-561). */}
        <span
          data-fold="zoom"
          data-away-at={rendered ? (steps?.zoomAt ?? FOLD.idle.zoomAt) : undefined}
          className={cn("flex shrink-0 items-center", FOLD.away)}
        >
          <Divider />
          {rendered ? <Zoom zoom={zoom.zoom} onZoom={zoom.onZoom} /> : <ZoomSkeleton />}
        </span>
        {rendered && (
          <MoreMenu
            bar={bar}
            zoom={zoom}
            experiences={open ? null : experiences}
            tools={open?.tools ?? []}
          />
        )}
        {/* The side panel's one button (KAN-586), always at the row's end,
            above where the panel opens: never folded away, since it is the
            only way back to a closed panel */}
        <Divider />
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-lg"
                aria-label={format.panelOpen ? "Hide Panel" : "Show Panel"}
                aria-pressed={format.panelOpen}
                disabled={format.disabled}
                className="aria-pressed:bg-brand-tint aria-pressed:text-brand shrink-0"
                onClick={format.onPanel}
              />
            }
          >
            <SidebarSimpleIcon aria-hidden className="-scale-x-100" />
          </TooltipTrigger>
          <TooltipContent>{format.panelOpen ? "Hide Panel" : "Show Panel"}</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

/**
 * Folds the bar until it fits (KAN-799, ./bar-fold.tsx): from nothing
 * folded, each step in turn (`data-word-at` sets `data-words-folded` on its
 * box, so the word under it goes; `data-away-at` sets `data-away`, so the
 * box goes and More lists it), until the row is no wider than the bar. It
 * runs whenever what the row holds (`contents`) or the bar's width changes,
 * before paint, so no step is drawn half done.
 */
function useFoldToFit(bar: RefObject<HTMLDivElement | null>, contents: string) {
  const fit = () => {
    const row = bar.current;
    if (!row) return;
    // A box that changed state may keep a mark its new step does not set
    for (const box of row.querySelectorAll("[data-away], [data-words-folded]")) {
      box.removeAttribute("data-away");
      box.removeAttribute("data-words-folded");
    }
    const words = [...row.querySelectorAll<HTMLElement>("[data-word-at]")];
    const aways = [...row.querySelectorAll<HTMLElement>("[data-away-at]")];
    const at = (box: HTMLElement, step: "wordAt" | "awayAt") => Number(box.dataset[step]);
    const last = Math.max(
      0,
      ...words.map((w) => at(w, "wordAt")),
      ...aways.map((a) => at(a, "awayAt")),
    );
    for (let step = 0; step <= last; step++) {
      for (const w of words) w.toggleAttribute("data-words-folded", step >= at(w, "wordAt"));
      for (const a of aways) a.toggleAttribute("data-away", step >= at(a, "awayAt"));
      row.toggleAttribute(
        "data-some-away",
        step > 0 && aways.some((a) => a.hasAttribute("data-away")),
      );
      if (row.scrollWidth <= row.clientWidth) return;
    }
  };
  // The latest `fit` for the observer, which outlives a render
  const latest = useRef(fit);
  useLayoutEffect(() => {
    latest.current = fit;
    fit();
  }, [contents]); // eslint-disable-line react-hooks/exhaustive-deps -- measures again only when the row's contents change
  useEffect(() => {
    const row = bar.current;
    if (!row) return;
    let width = row.clientWidth;
    const observer = new ResizeObserver(() => {
      if (row.clientWidth === width) return;
      width = row.clientWidth;
      latest.current();
    });
    observer.observe(row);
    return () => observer.disconnect();
  }, [bar]);
}

/** The bar's middle with a line open: its kind of text's size, a bullet's
 *  bold and italic, its tools, then Done. */
function LineGroup({ open, format }: { open: OpenLine; format: FormatTools }) {
  return (
    <>
      <div role="group" aria-label={open.role.label} className="flex shrink-0 items-center gap-1">
        <span data-word-at={FOLD.line.roleWordAt} className="flex">
          <span className={cn("text-note text-ink-muted pl-1 font-medium", FOLD.word)}>
            {open.role.label}
          </span>
        </span>
        <SizeStepper
          role={open.role}
          page={format.page}
          disabled={format.disabled}
          onChange={format.onChange}
        />
      </div>
      {open.marks && <MarkTools />}
      {open.tools.length > 0 && <Divider />}
      {open.tools.map((tool) => (
        <span
          key={tool.key}
          data-fold={tool.key}
          data-away-at={FOLD.line.toolAt[tool.leaves]}
          data-word-at={tool.glyph ? undefined : FOLD.line.toolWordsAt}
          className={cn("flex shrink-0", FOLD.away)}
        >
          <BarTool tool={tool} />
        </span>
      ))}
      <span data-word-at={FOLD.line.doneWordAt} className="flex shrink-0">
        <FoldButton
          label="Done"
          hint="Or press Esc"
          icon={<CheckIcon />}
          fold={FOLD.word}
          render={<Button variant="secondary" size="sm" onClick={open.onDone} />}
        />
      </span>
    </>
  );
}

/** A line tool on the desktop bar: a ghost glyph, or a secondary button
 *  whose word folds away on a narrow bar. A tool with no glyph keeps its
 *  word, and leaves the row for More instead. */
function BarTool({ tool }: { tool: LineTool }) {
  if (tool.glyph) {
    return (
      <Tip label={tool.label}>
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label={tool.label}
          disabled={tool.disabled}
          onClick={tool.onClick}
        >
          {tool.icon}
        </Button>
      </Tip>
    );
  }
  return (
    <FoldButton
      label={tool.label}
      hint={tool.hint}
      icon={tool.icon}
      fold={tool.icon ? FOLD.word : ""}
      disabled={tool.disabled}
      render={
        tool.href ? (
          <Link href={tool.href} className={buttonClasses({ variant: "secondary", size: "sm" })} />
        ) : (
          <Button variant="secondary" size="sm" disabled={tool.disabled} onClick={tool.onClick} />
        )
      }
    />
  );
}

/** Bold and italic for the open bullet, lit while the selection has them,
 *  as Docs does. The bar keeps the focus in the field, so the browser acts on
 *  the selection and the field reports the change as typing. The phone's
 *  line sheet draws the same two (KAN-799). */
export function MarkTools() {
  const [on, setOn] = useState({ bold: false, italic: false });
  useEffect(() => {
    const read = () =>
      setOn({
        bold: document.queryCommandState("bold"),
        italic: document.queryCommandState("italic"),
      });
    read();
    document.addEventListener("selectionchange", read);
    return () => document.removeEventListener("selectionchange", read);
  }, []);
  const press = (mark: "bold" | "italic") => {
    document.execCommand(mark);
    setOn((was) => ({ ...was, [mark]: document.queryCommandState(mark) }));
  };
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <Tip label="Bold">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Bold"
          aria-pressed={on.bold}
          className={cn(on.bold && ON)}
          onClick={() => press("bold")}
        >
          <TextBIcon aria-hidden />
        </Button>
      </Tip>
      <Tip label="Italic">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Italic"
          aria-pressed={on.italic}
          className={cn(on.italic && ON)}
          onClick={() => press("italic")}
        >
          <TextItalicIcon aria-hidden />
        </Button>
      </Tip>
    </div>
  );
}

/**
 * Undo and Redo, first on the slim bar in both its states (KAN-391). Each
 * goes back or forward one step of `HISTORY_STEPS`; Cmd+Z and Shift+Cmd+Z do
 * the same off a field. A Fit to One Page is one step too. The phone's bar
 * draws the same two (`HistoryButtons`).
 */
function History({ tools }: { tools: HistoryTools }) {
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <HistoryButtons tools={tools} />
    </div>
  );
}

/** Undo and Redo as ghost glyphs, on the desktop bar and the phone's. */
export function HistoryButtons({ tools }: { tools: HistoryTools }) {
  return (
    <>
      <Tip label="Undo">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Undo"
          disabled={!tools.canUndo}
          onClick={tools.onUndo}
        >
          <ArrowUUpLeftIcon aria-hidden />
        </Button>
      </Tip>
      <Tip label="Redo">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Redo"
          disabled={!tools.canRedo}
          onClick={tools.onRedo}
        >
          <ArrowUUpRightIcon aria-hidden />
        </Button>
      </Tip>
    </>
  );
}

/**
 * The slim bar's More (⋯), at the row's end once a control has left a
 * narrow bar (./bar-fold.tsx), as Docs keeps its own. It lists only what
 * has left: on open it reads which `data-fold` boxes the bar hides, so the
 * row's classes and fold steps alone decide, and nothing is listed twice. A
 * panel's item is checked while its panel is open, as its button is
 * pressed. With a line open it lists the line's tools that have left too.
 */
function MoreMenu({
  bar,
  zoom,
  experiences,
  tools,
}: {
  bar: RefObject<HTMLDivElement | null>;
  zoom: ZoomTools;
  experiences: ExperiencesTools | null;
  tools: LineTool[];
}) {
  const router = useRouter();
  const [away, setAway] = useState<ReadonlySet<string>>(new Set());
  const read = () => {
    const boxes = bar.current?.querySelectorAll<HTMLElement>("[data-fold]") ?? [];
    setAway(
      new Set([...boxes].filter((box) => box.offsetWidth === 0).map((box) => box.dataset.fold!)),
    );
  };
  return (
    <span className={cn("shrink-0", FOLD.more)}>
      <DropdownMenu onOpenChange={(open) => open && read()}>
        <Tooltip>
          <TooltipTrigger
            render={
              <DropdownMenuTrigger
                render={<Button variant="ghost" size="icon-lg" aria-label="More Tools" />}
              />
            }
          >
            <EllipsisIcon className="size-5" />
          </TooltipTrigger>
          <TooltipContent>More Tools</TooltipContent>
        </Tooltip>
        <DropdownMenuContent data-keeps-selection align="end" className="w-auto min-w-52">
          {tools
            .filter((tool) => away.has(tool.key))
            .map((tool) => (
              <DropdownMenuItem
                key={tool.key}
                disabled={tool.disabled}
                onClick={() => (tool.href ? router.push(tool.href) : tool.onClick?.())}
              >
                {tool.icon} {tool.label}
              </DropdownMenuItem>
            ))}
          {experiences?.picker && away.has("experiences") && (
            <DropdownMenuCheckboxItem
              checked={experiences.picker.open}
              onCheckedChange={experiences.picker.onToggle}
            >
              <StackIcon aria-hidden /> Add Experiences
            </DropdownMenuCheckboxItem>
          )}
          {experiences?.cut && away.has("cut") && (
            <DropdownMenuCheckboxItem
              checked={experiences.cut.open}
              onCheckedChange={experiences.cut.onToggle}
            >
              <ScissorsIcon aria-hidden /> Cut From Resume
            </DropdownMenuCheckboxItem>
          )}
          {away.has("zoom") && <ZoomSubmenu zoom={zoom.zoom} onZoom={zoom.onZoom} />}
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  );
}

/**
 * What sits beside the page on Tailor's review, as icons in the title row,
 * before Download, where Google Docs keeps its own (KAN-499): Original, the
 * file every resume wears, and Suggestions, a lightbulb with the count left,
 * each tinted while its column is open and closing it when pressed again.
 * Suggestions is the review's one control for them (KAN-799): a Show and Hide
 * Suggestions toggle for the marks on the page sat in the bar beside it, and
 * it is the panel's own now. 36px, as every icon button in the bar is; they
 * were 40px.
 */
export function ReviewButtons({ review }: { review: ReviewTools }) {
  const button = (
    side: "suggestions" | "original",
    label: string,
    Icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>,
    count = 0,
  ) => {
    const open = review.side === side;
    return (
      <IconButton
        label={count > 0 ? `${label}, ${count}` : label}
        tooltip={label}
        aria-pressed={open}
        className={cn(
          "hover:bg-ink/5 size-9 rounded-full after:inset-0",
          open && "bg-brand/10 text-brand hover:bg-brand/10 hover:text-brand",
        )}
        onClick={() => review.onSide(open ? null : side)}
      >
        <Icon aria-hidden className="size-5" />
        {count > 0 && (
          <span className="bg-brand text-on-brand text-note absolute -top-1 -right-1 flex h-4.5 min-w-4.5 items-center justify-center rounded-full px-1 font-semibold tabular-nums">
            {count}
          </span>
        )}
      </IconButton>
    );
  };
  return (
    <>
      {review.hasOriginal && button("original", "Original Resume", FileIcon)}
      {button("suggestions", "Suggestions", LightbulbIcon, review.count)}
    </>
  );
}

/** The way back to one page, on the idle bar only while the resume runs
 *  over it. It is the action itself: an amber "2 pages" chip with a caret
 *  came first, whose click opened a card holding this button (2026-11-01).
 *  The count and what it does are in its tooltip. Its own glyph, lines
 *  pressed together (KAN-799): it shared Cut From Resume's scissors. */
function FitButton({
  pages,
  linesOver,
  disabled,
  fitting,
  onFit,
}: {
  pages: number;
  linesOver: number;
  disabled: boolean;
  /** While a fit runs it reads "Fitting…" with a spinner. Not a modal: the
   *  page stays in view, where each cycle's cuts close up as they come
   *  (KAN-584), the progress a modal would cover. */
  fitting: boolean;
  onFit: () => void;
}) {
  const over =
    linesOver > 0
      ? `About ${linesOver} ${linesOver === 1 ? "line runs" : "lines run"} onto page 2.`
      : `It runs to ${pages} pages.`;
  return (
    <FoldButton
      label={fitting ? "Fitting…" : "Fit to One Page"}
      hint={`${over} This hides the least useful lines until it fits.`}
      icon={
        fitting ? (
          <CircleNotchIcon aria-hidden className="animate-spin motion-reduce:animate-none" />
        ) : (
          <ArrowsInLineVerticalIcon aria-hidden />
        )
      }
      fold={FOLD.word}
      disabled={disabled}
      render={
        <Button
          variant="secondary"
          size="sm"
          data-bar-action
          className="shrink-0"
          disabled={disabled}
          onClick={onFit}
        />
      }
    />
  );
}

/** The zoom control (./zoom.tsx) as a bar, until the first render lands. */
function ZoomSkeleton() {
  return <Skeleton aria-hidden="true" className="h-7 w-20 shrink-0" />;
}
