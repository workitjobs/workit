"use client";

import {
  ArrowLeftIcon,
  CaretLeftIcon,
  CaretRightIcon,
  MagnifyingGlassMinusIcon,
  MagnifyingGlassPlusIcon,
  ScissorsIcon,
  StackIcon,
  XIcon,
} from "@phosphor-icons/react/ssr";
import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type MouseEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { SparkleIcon } from "@/components/icons";
import { ASK_SCOUT_LIVE } from "@/components/scout/scout-buttons";
import { Button } from "@/components/ui/button";
import { TabButtons } from "@/components/ui/tabs";
import type { Bank } from "@/lib/bank-actions";
import type {
  Choices,
  ChoicesUpdate,
  PageSettings,
  RenderBox,
  RenderedPdf,
} from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

import { DownloadMenu, DownloadNotes, type ResumeDownload } from "../download-menu";
import { useBack } from "../../back-link";
import { EDITOR_PARENT } from "./back";
import { cutLeft as anyCutLeft, lineName, type FitCuts, type Line } from "./model";
import {
  FitButton,
  HistoryButtons,
  PanelToggle,
  ReviewButtons,
  SaveStatus,
  SheetTool,
  lineTools,
  type HistoryTools,
  type LineHandlers,
  type PanelTab,
} from "./toolbar";
import { FormatOptions } from "./page-format";
import { FoldButton, PHONE_FOLD } from "./bar-fold";
import { BAR_BUTTONS, PRESSED_GLYPH, SLIM_BAR } from "./slim-bar";
import { boxKey, kindLabel } from "./pdf-pages";
import { CutPicker, ExperiencesPicker } from "./experiences-picker";
import { Tip } from "@/components/ui/tip";

/**
 * The phone editor (KAN-219, the KAN-201 prototype's variant A). The page
 * fills the width and stays the editor: tap a line and a bottom sheet slides
 * up with that line in a 16 px field, its actions at 44 pt, and previous and
 * next arrows that step through the lines in page order, so a mis-tap on a
 * 7 px line costs one arrow press. The sheet has no scrim: the page above it
 * still scrolls and takes taps. Zoom draws the page at two times the width.
 * The whole layout is sized to the visual viewport, because the iOS keyboard
 * covers the layout viewport instead of shrinking it; sized this way the
 * sheet stays above the keyboard. The desktop editor owns the state and the
 * saves; this file only lays them out. Its two rows are the desktop's
 * (KAN-586): the title row, then the toolbar with the page's tools and the
 * side panel's button, whose Sections and Format tabs open in a sheet.
 * "Ask Scout", while `ASK_SCOUT_LIVE`, opens the assistant (KAN-221) in its
 * own sheet.
 *
 * The layer renders in a portal to `<body>` (KAN-574): the seeker shell's
 * `@container/main` is a containing block, so `fixed` inside it was fixed
 * to the page area, not the window. The layer sat 64px low under the
 * shell's bar, and the bottom bar it had then (Add Experiences, Cut From
 * Resume, Suggestions) ended past the screen's foot.
 */

/** Below this width the editor takes the phone layout. */
const PHONE_QUERY = "(max-width: 40rem)";
/** 44 pt, Apple's smallest touch target, for every control in the sheet. */
const TAP = "[&_button]:min-h-11 [&_button]:min-w-11";
/** 16 px: below this, iOS Safari zooms the page when the field gets focus. */
export const PHONE_FIELD =
  "bg-panel text-ink ring-border-subtle focus:ring-brand w-full resize-none rounded-control px-3 py-2.5 text-base ring-1 outline-none focus:ring-2";

function subscribeQuery(onChange: () => void) {
  const query = window.matchMedia(PHONE_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** True on a phone-width screen; false on the server, so the first paint is desktop's. */
export function usePhone() {
  return useSyncExternalStore(
    subscribeQuery,
    () => window.matchMedia(PHONE_QUERY).matches,
    () => false,
  );
}

function subscribeViewport(onChange: () => void) {
  const viewport = window.visualViewport;
  viewport?.addEventListener("resize", onChange);
  viewport?.addEventListener("scroll", onChange);
  window.addEventListener("resize", onChange);
  return () => {
    viewport?.removeEventListener("resize", onChange);
    viewport?.removeEventListener("scroll", onChange);
    window.removeEventListener("resize", onChange);
  };
}

/** The visual viewport's height and offset, as "height|top". */
function viewportSnapshot() {
  const viewport = window.visualViewport;
  return `${viewport?.height ?? window.innerHeight}|${viewport?.offsetTop ?? 0}`;
}

/** Each box's line once, in page order: by page, then top to bottom, then left to right. */
export function pageOrder(boxes: RenderBox[]) {
  const sorted = [...boxes].sort((a, b) => a.page - b.page || a.y0 - b.y0 || a.x0 - b.x0);
  return [...new Set(sorted.map(boxKey))];
}

export function PhoneEditor({
  rendered,
  title,
  pages,
  bank,
  choices,
  selected,
  line,
  box,
  text,
  bulletField,
  saving,
  fitting,
  error,
  download,
  bar,
  back: backTo,
  page,
  onPage,
  suggestions,
  handlers,
  assistant,
  panel,
  onSelect,
  onType,
  onFlush,
  onApply,
  onFit,
  history,
  cuts,
}: {
  /** Null until the first render lands (./editor.tsx streams it in). */
  rendered: RenderedPdf | null;
  /** The resume's name, as the desktop's title row draws it (renamed in
   *  place). */
  title: ReactNode;
  /** The page area, drawn by the editor: the PDF, or its skeleton while the
   *  first render is on its way, from the same unawaited render the desktop
   *  layout reads. */
  pages: ReactNode;
  bank: Bank;
  choices: Choices;
  selected: string | null;
  line: Line | null;
  box: RenderBox | undefined;
  /** The selected line's typed text, or null when it is not typed in place. */
  text: string | null;
  /** A bullet's own field, the desktop's rich one, so bold and italic show
   *  in its words (KAN-799); null for any other line. */
  bulletField: (() => ReactNode) | null;
  saving: boolean;
  /** A Fit to One Page is under way, as on the desktop bar. */
  fitting: boolean;
  error: string | null;
  /** The page's settings, in the panel's Format tab (./page-format.tsx). */
  page: PageSettings;
  onPage: (next: PageSettings) => void;
  /** The resume's downloads, the same as the desktop sticky bar's. */
  download: ResumeDownload;
  /** The page's own row under the buttons: on Tailor's review the job,
   *  the step and Finish, which the layer covers on the page. */
  bar?: ReactNode;
  /** Where the arrow goes, when not to the page that opened the editor
   *  (`useBack`): Tailor's review goes to the step before. */
  back?: { href: string; label: string; onClick?: (event: MouseEvent) => void };
  /** Tailor's Suggestions panel, in a sheet opened from the toolbar. */
  suggestions?: {
    count: number;
    panel: ReactNode;
    open: boolean;
    onOpenChange: (open: boolean) => void;
  } | null;
  /** What the selected line's tools act through: the sheet draws the
   *  desktop bar's own (`lineTools`), the arrows alone. */
  handlers: LineHandlers;
  /** The editor assistant (KAN-221), shown in a sheet when asked for. */
  assistant: ReactNode;
  /** The side panel (KAN-586), in a sheet: its tabs, Sections and Format,
   *  opened by the toolbar's panel button, and on Sections' Header row
   *  when the page's header line is tapped. */
  panel: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    tab: PanelTab;
    onTab: (tab: PanelTab) => void;
    sections: ReactNode;
  };
  onSelect: (key: string | null) => void;
  onType: (text: string) => void;
  onFlush: () => void;
  onApply: (changes: ChoicesUpdate) => void;
  onFit: () => void;
  /** Undo and Redo, the desktop bar's: a Fit to One Page is one step. */
  history: HistoryTools;
  /** What Fit to One Page cut, for Cut From Resume. */
  cuts: FitCuts;
}) {
  const opener = useBack(EDITOR_PARENT);
  const back = backTo ?? opener;
  const snapshot = useSyncExternalStore(subscribeViewport, viewportSnapshot, () => "0|0");
  const [height, top] = snapshot.split("|").map(Number);
  const [zoom, setZoom] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [cutOpen, setCutOpen] = useState(false);
  const cutLeft = anyCutLeft(bank, choices, cuts);
  const [asking, setAsking] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  const order = pageOrder(rendered?.boxes ?? []);
  const at = selected ? order.indexOf(selected) : -1;

  // Bring the selected line to the middle of the page area, also after an arrow press
  useEffect(() => {
    if (!selected) return;
    scroller.current
      ?.querySelector('[aria-pressed="true"]')
      ?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  }, [selected, zoom]);

  // Mounted only after hydration (`usePhone` is false on the server), so
  // `document` is there.
  return createPortal(
    <div
      className="bg-app fixed inset-x-0 top-0 z-40 flex flex-col overflow-hidden"
      style={{ height: height || "100dvh", transform: `translateY(${top}px)` }}
    >
      {/* The desktop's own two rows, on the page's ground (KAN-586): the
          title row (the way back, the name, whether it is saved, and
          Download, the page's one filled button), then the toolbar, tools
          only, in the desktop bar's white box. Until then the phone kept
          the old bar: a lavender band with an amber "lines over" notice,
          Format and Zoom as worded buttons, and a bottom bar of Add
          Experiences and Cut From Resume */}
      <header className="bg-app/95 border-border-surface flex flex-col gap-2 border-b px-3 pt-2 pb-2 backdrop-blur">
        <div className="@container/title flex items-center gap-1">
          <Link
            href={back.href}
            aria-label={back.label}
            onClick={back.onClick}
            // A fill on the press (and under a pointer, or a keyboard's
            // ring): the phone's back arrow gave no sign it was touched.
            className="text-ink hover:bg-ink/5 active:bg-ink/10 focus-visible:ring-brand-ring -ml-1 flex size-11 shrink-0 items-center justify-center rounded-full transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
          >
            <ArrowLeftIcon aria-hidden className="size-5" />
          </Link>
          <div className="min-w-0 flex-1">{title}</div>
          <SaveStatus saving={saving} fitting={fitting} ready={Boolean(rendered)} short />
          <span className={cn("flex shrink-0", TAP)}>
            <DownloadMenu
              download={download}
              fold={PHONE_FOLD.downloadWord}
              secondary={Boolean(bar)}
            />
          </span>
        </div>
        {/* One row at every width: the words fold (`PHONE_FOLD`) */}
        <div className={cn(SLIM_BAR, "@container/bar static", TAP)}>
          <HistoryButtons tools={history} />
          {/* Each waits for the first render: each acts through a new one */}
          {!suggestions && (
            <FoldButton
              label="Add Experiences"
              icon={<StackIcon aria-hidden />}
              fold={PHONE_FOLD.experiencesWord}
              disabled={!rendered}
              render={
                <Button
                  variant="secondary"
                  size="sm"
                  className="shrink-0"
                  disabled={!rendered}
                  onClick={() => setPickerOpen(true)}
                />
              }
            />
          )}
          {rendered && rendered.page_count > 1 && (
            <FitButton
              pages={rendered.page_count}
              linesOver={rendered.lines_over}
              disabled={saving}
              fitting={fitting}
              onFit={onFit}
              fold={PHONE_FOLD.fitWord}
            />
          )}
          {cutLeft && (
            <FoldButton
              label="Cut From Resume"
              icon={<ScissorsIcon aria-hidden />}
              fold="sr-only"
              disabled={!rendered}
              render={
                <Button
                  variant="secondary"
                  size="sm"
                  className="text-warning hover:text-warning shrink-0"
                  disabled={!rendered}
                  onClick={() => setCutOpen(true)}
                />
              }
            />
          )}
          {/* Not drawn at all while Scout is off: a greyed Ask Scout read
              as broken (the user's call, 2026-11-11) */}
          {ASK_SCOUT_LIVE && (
            <FoldButton
              label="Ask Scout"
              icon={<SparkleIcon />}
              fold="sr-only"
              disabled={!rendered}
              render={
                <Button
                  variant="secondary"
                  size="sm"
                  className="shrink-0"
                  disabled={!rendered}
                  onClick={() => setAsking(true)}
                />
              }
            />
          )}
          <div className="ml-auto flex shrink-0 items-center gap-1">
            {suggestions && (
              <ReviewButtons
                review={{
                  count: suggestions.count,
                  side: suggestions.open ? "suggestions" : null,
                  onSide: (side) => suggestions.onOpenChange(side === "suggestions"),
                  hasOriginal: false,
                }}
              />
            )}
            <Tip label={zoom ? "Fit Width" : "Zoom In"}>
              <Button
                variant="ghost"
                size="icon-lg"
                aria-label={zoom ? "Fit Width" : "Zoom In"}
                aria-pressed={zoom}
                className={PRESSED_GLYPH}
                onClick={() => setZoom(!zoom)}
              >
                {zoom ? (
                  <MagnifyingGlassMinusIcon aria-hidden />
                ) : (
                  <MagnifyingGlassPlusIcon aria-hidden />
                )}
              </Button>
            </Tip>
            <PanelToggle
              open={panel.open}
              disabled={!rendered}
              onToggle={() => panel.onOpenChange(!panel.open)}
            />
          </div>
        </div>
        {bar && <div className={cn(TAP, "[&_a]:min-h-11")}>{bar}</div>}
        {error && (
          <p role="alert" className="text-note text-danger">
            {error}
          </p>
        )}
        <DownloadNotes download={download} />
      </header>

      <div
        ref={scroller}
        className={cn(
          "min-h-0 flex-1 overflow-auto overscroll-none p-4",
          selected || suggestions?.open || panel.open ? "pb-[70vh]" : "pb-6",
        )}
      >
        <div className={zoom ? "w-[200%]" : "w-full"}>{pages}</div>
      </div>

      {/* No scrim: the page above the sheet still scrolls and takes taps */}
      {selected && line && box && (
        <Sheet
          onClose={() => onSelect(null)}
          title={
            <div className="flex min-w-0 items-center gap-1">
              <Button
                variant="secondary"
                size="sm"
                aria-label="Previous Line"
                disabled={at <= 0}
                onClick={() => onSelect(order[at - 1])}
              >
                <CaretLeftIcon aria-hidden />
              </Button>
              <span className="text-label text-ink-meta min-w-0 flex-1 truncate text-center font-semibold">
                {kindLabel(box.kind)} · {lineName(line)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                aria-label="Next Line"
                disabled={at < 0 || at >= order.length - 1}
                onClick={() => onSelect(order[at + 1])}
              >
                <CaretRightIcon aria-hidden />
              </Button>
            </div>
          }
        >
          {text != null &&
            (line.kind === "bullet" ? (
              bulletField?.()
            ) : (
              <input
                aria-label={kindLabel(box.kind)}
                value={text}
                enterKeyHint="done"
                onChange={(e) => onType(e.target.value)}
                onBlur={onFlush}
                onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                className={PHONE_FIELD}
              />
            ))}
          {/* The desktop bar's tools (`lineTools`): the arrows alone, as on
              the desktop (KAN-586). Size, Show or Hide, Add Bullet and Edit
              Header live in the side panel, bold and italic in the keys */}
          <div className={cn("flex flex-wrap items-center gap-2", TAP, BAR_BUTTONS)}>
            {lineTools(line, choices, handlers).map((tool) => (
              <SheetTool key={tool.key} tool={tool} />
            ))}
            {ASK_SCOUT_LIVE && (
              <Button variant="secondary" size="sm" onClick={() => setAsking(true)}>
                <SparkleIcon /> Ask Scout About This Line
              </Button>
            )}
          </div>
        </Sheet>
      )}

      {/* Kept mounted while closed, so the chat survives closing it */}
      <div className={cn("absolute inset-x-0 bottom-0 z-50 h-[70%]", !asking && "hidden")}>
        <Sheet onClose={() => setAsking(false)} title="Scout" fill>
          {assistant}
        </Sheet>
      </div>

      {/* No scrim, as a line's sheet: the outlined line shows above it */}
      {suggestions?.open && !selected && (
        <Sheet onClose={() => suggestions.onOpenChange(false)} title="Suggestions">
          <div className={TAP}>{suggestions.panel}</div>
        </Sheet>
      )}

      {cutOpen && (
        <>
          <div className="absolute inset-0 z-30 bg-black/25" onClick={() => setCutOpen(false)} />
          <Sheet onClose={() => setCutOpen(false)} title="Cut From Resume">
            <div className={TAP}>
              <CutPicker bank={bank} choices={choices} cuts={cuts} onApply={onApply} />
            </div>
          </Sheet>
        </>
      )}

      {/* The side panel (KAN-586), as beside the desktop's page: its tabs
          are the sheet's title, and its close is the sheet's own */}
      {panel.open && (
        <>
          <div
            className="absolute inset-0 z-30 bg-black/25"
            onClick={() => panel.onOpenChange(false)}
          />
          <Sheet
            onClose={() => panel.onOpenChange(false)}
            title={
              <TabButtons
                label="Side Panel"
                options={[
                  { value: "sections", label: "Sections" },
                  { value: "format", label: "Format" },
                ]}
                value={panel.tab}
                onChange={panel.onTab}
              />
            }
          >
            <div className={cn("flex flex-col gap-2", TAP)}>
              {panel.tab === "sections" ? (
                panel.sections
              ) : (
                <FormatOptions page={page} onChange={onPage} />
              )}
            </div>
          </Sheet>
        </>
      )}

      {pickerOpen && (
        <>
          <div className="absolute inset-0 z-30 bg-black/25" onClick={() => setPickerOpen(false)} />
          <Sheet onClose={() => setPickerOpen(false)} title="Experiences">
            <div className={TAP}>
              <ExperiencesPicker bank={bank} choices={choices} onApply={onApply} />
            </div>
          </Sheet>
        </>
      )}
    </div>,
    document.body,
  );
}

/** A panel that slides up from the bottom edge of the layout. */
function Sheet({
  title,
  onClose,
  children,
  fill = false,
}: {
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  /** The body fills the sheet's full height and scrolls itself (the chat). */
  fill?: boolean;
}) {
  return (
    <div
      className={cn(
        // A panel, so white as a card is: on the surface colour its own
        // secondary buttons showed only as outlines (KAN-258).
        "animate-rise bg-panel ring-border-subtle absolute inset-x-0 bottom-0 z-40 flex flex-col rounded-t-3xl shadow-lg ring-1",
        fill ? "h-full" : "max-h-[70%]",
      )}
      // A press on a button keeps focus in the field, so the keyboard stays up
      onMouseDown={(e) => {
        if ((e.target as HTMLElement).closest("button")) e.preventDefault();
      }}
    >
      <div className="bg-border-subtle mx-auto mt-2 h-1 w-10 rounded-full" />
      <div className={cn("flex items-center gap-2 px-4 pt-1", TAP)}>
        <div className="text-label text-ink-meta min-w-0 flex-1 truncate font-semibold">
          {title}
        </div>
        <Button variant="secondary" size="sm" aria-label="Close" onClick={onClose}>
          <XIcon aria-hidden />
        </Button>
      </div>
      {fill ? (
        <div className="flex min-h-0 flex-1 flex-col pt-2">{children}</div>
      ) : (
        <div className="flex min-h-0 flex-col gap-3 overflow-y-auto px-4 pt-2 pb-4">{children}</div>
      )}
    </div>
  );
}
