"use client";

import {
  columnOrderingFeature,
  columnPinningFeature,
  columnResizingFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnSizingState,
  type Header,
} from "@tanstack/react-table";
import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type DragEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { SortIcon, TailorIcon } from "@/components/icons";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/shadcn/table";
import { ClickableRow } from "@/components/clickable-row";
import { MatchBadge } from "@/components/match-badge";
import { Reflow } from "@/components/reflow";
import { useShallowPush } from "@/components/shallow-routing";
import { Card } from "@/components/ui/card";
import { STICKY_TH, TABLE_FILL, useFillPage } from "@/components/fill-page";
import { PlacesValue } from "@/components/places-value";
import { cn } from "@/lib/cn";

import { STAGE_ORDER } from "../stage-colors";
import { StageMenu } from "./[jobId]/tracker-controls";
import { ClosedSavedControl } from "./closed-saved";
import { LocalDate } from "../local-time";
import { isClosedSaved, sortKey, type Application } from "../tracker";
import { ApplicationTile } from "./application-tile";
import {
  COLUMNS,
  FROZEN,
  MAX_WIDTH,
  MIN_WIDTH,
  moveColumn,
  setColumnLayout,
  useColumnLayout,
  type ColumnId,
  type ColumnLayout,
} from "./column-layout";
import { applicationHref, applicationsHref, type Sort } from "./query";
import { useApplicationsQuery } from "./view-switcher";
import { ViewResumeButton } from "./view-resume";

/**
 * The applications as a table, one row each, in the order job trackers read
 * (KAN-256): what and who (Role, with its company under it), where it stands (Status, Date
 * Applied), how good it is (Match), the job's facts (Job Type;
 * Location; Work Model; Pay Range), and what was sent and whether it is still
 * open (Resume; Posting). Role stays frozen at the
 * left while the rest scrolls. Company and Role were two frozen columns
 * (KAN-256) until they took so much width that few other columns showed;
 * stacked in one again, the company's name is still filtered and sorted on
 * as its own field.
 *
 * Source and Notes / Next Step left the table (2026-11-05): the user found
 * them more than a row needs. Source, the hiring system the posting is on,
 * is on the application's page (./[jobId]/your-application.tsx) and stays a
 * filter here; Notes was a placeholder, since nothing stores notes yet.
 *
 * Status is the stage menu (./[jobId]/tracker-controls.tsx's StageMenu,
 * 2026-11-05), so a stage changes from the row as from a card; its cell
 * keeps a click, or a pick in its popup, from opening the application.
 *
 * Its frame follows the company Home's Recent Applicants
 * (company/applicants-preview.tsx): one white card, 12px grey headings,
 * rules between rows and no box around each.
 *
 * A TANSTACK TABLE V9 (KAN-282), as the company table is (company/table.tsx,
 * which says why v8 examples do not apply), so the seeker can arrange it as
 * a Notion table: drag a heading to a new place, resize a column by its
 * heading's right edge (or its arrow keys), and hide columns from the
 * Columns menu in the filter bar. That layout is this browser's
 * (./column-layout.ts); the frozen Role column cannot move or hide.
 *
 * SORTING IS IN THE URL, ?sort=, like every other choice on this page, so an
 * order can be shared and Back undoes it. A heading moves it in place
 * (components/shallow-routing.tsx): the rows are already here, and the table
 * sorts them itself. Five columns sort, each one way, the way it is read
 * (SORT_DESC): Role by its company A to Z (then by role, so a company's
 * roles sit together; `?sort=company`), Status furthest along first, Date Applied
 * latest first, Match best first, Pay Range best first. What has no value
 * to sort by goes last either way, in the order it came in. The rest do not
 * sort; the filters above the table pick those out. The heading in force
 * says so in aria-sort as well as in its chevron.
 *
 * IT SCROLLS SIDEWAYS, as a Notion table does, rather than dropping columns:
 * every column keeps its width (a fixed table layout, each width from the
 * layout) and cuts what does not fit, with the whole value on hover. A last,
 * empty column takes whatever room is left, so a resize never stretches the
 * others. A row opens its application's own page (./[jobId]) on a click
 * anywhere (components/clickable-row.tsx); the role is its link.
 */
const FEATURES = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { basic: sortFn_basic, text: sortFn_text },
  columnOrderingFeature,
  columnPinningFeature,
  columnSizingFeature,
  columnResizingFeature,
  columnVisibilityFeature,
});

/** Which way each sortable column runs, for the sort, aria-sort and the
 *  chevron. */
const SORT_DESC: Record<Sort, boolean> = {
  company: false,
  status: true,
  applied: true,
  match: true,
  pay: true,
};

/** What a sortable column sorts by; undefined sorts last. The company
 *  sort keeps a company's roles together, A to Z within it. */
const SORT_VALUE: Record<Sort, (app: Application) => string | number | undefined> = {
  company: (app) => `${app.company}\u0000${app.role}`,
  status: (app) => STAGE_ORDER.indexOf(app.stage),
  applied: (app) => (app.appliedOn ? sortKey(app.appliedOn) : undefined),
  match: (app) => app.match ?? undefined,
  pay: (app) => app.payPerYear ?? undefined,
};

/** The sort each sortable column's heading picks. Role's is `company`: the
 *  merged column sorts by its company, the URL keeping the older name. */
const COLUMN_SORT: Partial<Record<ColumnId, Sort>> = {
  role: "company",
  status: "status",
  applied: "applied",
  match: "match",
  pay: "pay",
};

/** The column a sort is drawn on. */
const SORT_COLUMN = Object.fromEntries(
  Object.entries(COLUMN_SORT).map(([id, sort]) => [sort, id]),
) as Record<Sort, ColumnId>;

/** What a sort's heading says it sorts by, when that is not the heading. */
const SORT_HINT: Partial<Record<Sort, string>> = { company: "Sort by company, A to Z" };

/** A fact cell's value as plain text, or a faint dash where the job has
 *  none, its word ("Not listed") for a screen reader (2026-11-10). Each
 *  cell drew its column's glyph (a calendar, a pin, a briefcase) and
 *  "Not yet", "Not listed", "Not scored", "Not sent" in about a fifth of
 *  them: the column's heading already names it, and the words were noise.
 *  The cards (./cards.tsx) keep the glyphs, where nothing else names a
 *  fact. */
function FactValue({
  value,
  missing,
  title,
}: {
  value: ReactNode;
  missing: string;
  title?: string;
}) {
  const has = value != null && value !== "";
  return has ? (
    <span title={title} className="block truncate">
      {value}
    </span>
  ) : (
    <Missing word={missing} />
  );
}

/** A cell with nothing to show: a faint dash, the word for a screen reader. */
function Missing({ word }: { word: string }) {
  return (
    <span className="text-ink-faint">
      <span aria-hidden="true">—</span>
      <span className="sr-only">{word}</span>
    </span>
  );
}

/** Each column's cell. The cells are drawn as the job cards draw their facts
 *  (ui/fact.tsx); Status, Match and Posting are pills. */
const CELL: Record<ColumnId, (app: Application) => ReactNode> = {
  // The logo, then the role over its company, as the list drew it before
  // KAN-256. The role is cut to the column (at two lines in a phone's
  // 208px column, one from 672px of page), the whole title on hover:
  // scraped titles run long ("... 2027 in Eurasburg / Bavaria"). The row
  // opens on a click anywhere (components/clickable-row.tsx); the role is the link a
  // keyboard reaches.
  role: (app) => (
    <div className="flex min-w-0 items-center gap-3">
      <ApplicationTile application={app} size="sm" muted={isClosedSaved(app)} />
      <div className="min-w-0">
        <Link
          href={applicationHref(app.id)}
          title={app.role}
          className="text-label text-ink hover:text-brand focus-visible:ring-brand-ring -my-1 block truncate rounded-xs py-1 font-semibold transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none @max-2xl/main:line-clamp-2 @max-2xl/main:whitespace-normal"
        >
          {app.role}
        </Link>
        <div className="flex min-w-0 items-center gap-1.5">
          <p className="text-note text-ink-meta truncate" title={app.company}>
            {app.company}
          </p>
          {/* A resume made for this job, ready to send (KAN-217). */}
          {/* Tailored as a word beside the company, not a pill: the
              pill stood 8px taller than the line, so a row with one was
              taller than a row without (2026-11-10). */}
          {app.tailored && (
            <span className="text-note text-brand inline-flex shrink-0 items-center gap-1">
              <TailorIcon className="size-3.5" />
              Tailored
            </span>
          )}
        </div>
      </div>
    </div>
  ),
  // The stage menu, as on a card and the application's page: a stage
  // changes from the row, without opening the application.
  status: (app) =>
    isClosedSaved(app) ? (
      <ClosedSavedControl app={app} />
    ) : (
      <StageMenu jobId={app.id} stage={app.stage} placeholder="Saved" className="w-full" compact />
    ),
  applied: (app) => (
    <FactValue
      value={app.appliedOn ? <LocalDate at={app.appliedOn} /> : null}
      missing="Not applied yet"
    />
  ),
  match: (app) =>
    app.match != null ? <MatchBadge score={app.match} /> : <Missing word="Not scored" />,
  track: (app) => <FactValue value={app.track} missing="Not listed" />,
  // Several places: the first, then "+N more", which opens them all.
  location: (app) =>
    (app.places?.length ?? 0) > 1 ? (
      <PlacesValue places={app.places ?? []} />
    ) : (
      <FactValue value={app.location} missing="Not listed" title={app.location ?? undefined} />
    ),
  workModel: (app) => <FactValue value={app.workModel} missing="Not listed" />,
  pay: (app) => <FactValue value={app.pay} missing="Not listed" />,
  // View Resume (KAN-267), a quiet text button, as Auto Apply's is.
  resume: (app) =>
    app.sentResume ? (
      <ViewResumeButton resume={app.sentResume} quiet />
    ) : (
      <Missing word="Not sent" />
    ),
};

const helper = createColumnHelper<typeof FEATURES, Application>();

/** Built once: `columns` must keep its identity between renders. */
const COLUMN_DEFS = helper.columns(
  COLUMNS.map(({ id, label, width }) =>
    helper.accessor((app) => (COLUMN_SORT[id] ? SORT_VALUE[COLUMN_SORT[id]](app) : undefined), {
      id,
      header: label,
      size: width,
      minSize: MIN_WIDTH,
      maxSize: MAX_WIDTH,
      enableSorting: COLUMN_SORT[id] != null,
      sortFn: COLUMN_SORT[id] === "company" ? "text" : "basic",
      sortUndefined: "last",
    }),
  ),
);

const PINNING = { start: FROZEN, end: [] };

/** The columns whose cells are one control or score each (a match pill,
 *  View): centred under a centred heading, by the table rule in
 *  frontend/docs/design.md (2026-11-10). Text columns stay left-aligned. */
const CENTRED: ColumnId[] = ["match", "resume"];

const TH = "px-4 text-note text-ink-meta font-medium";
/** A plain fact cell: one line of note text in ink, as easy to read as the
 *  role; it was grey, which read as disabled (KAN-256). */
const TD = "px-4 text-note text-ink";
/** A frozen cell paints the row's own background (white, the hover tint
 *  with the row) so scrolled cells don't show through. FROZEN AT EVERY
 *  WIDTH (2026-11-10). Job starts at 320px, about a phone's whole table,
 *  so below 672px of page (`PHONE_JOB`) it is 208px instead, and Status
 *  shows beside it. Until then it was frozen only from 672px and scrolled
 *  with the rest below that, so a phone's table showed the job alone, cut
 *  Status in half at its edge, and gave no sign the stage was there. Its
 *  place is a custom property, not `left`, which would shift a narrow
 *  page's `relative` heading. */
const FROZEN_CELL = "z-1 bg-panel sticky left-(--frozen-left)";
/** The last frozen column draws the edge the scrolled cells pass under: a
 *  shadow, since a collapsed table's borders don't move with a sticky cell. */
const FROZEN_EDGE = "shadow-[1px_0_0_var(--color-border-subtle)]";
/** The Job column's width below 672px of page, over its kept width
 *  (`!`, since the kept width is an inline style): 208px leaves a phone's
 *  table room for most of Status beside it. */
const PHONE_JOB = "@max-2xl/main:w-52!";
const FROZEN_HOVER = "group-hover/row:bg-hover transition-colors";

/** How far one arrow key press resizes a column. */
const KEY_STEP = 16;

/**
 * Whether the table runs on past its card's right edge from where it is
 * scrolled to: then a fade at the edge says there is more (2026-11-10). It
 * ran 400px past a 1440px window's card, cut a heading mid-word ("Pay
 * Ran…") and gave no sign it scrolled. Read again on a scroll and a resize.
 */
function useMoreToRight() {
  const ref = useRef<HTMLElement>(null);
  const [more, setMore] = useState(false);
  useEffect(() => {
    const box = ref.current?.querySelector<HTMLElement>('[data-slot="table-container"]');
    if (!box) return;
    const read = () => setMore(box.scrollLeft + box.clientWidth < box.scrollWidth - 1);
    read();
    box.addEventListener("scroll", read, { passive: true });
    const observer = new ResizeObserver(read);
    observer.observe(box);
    if (box.firstElementChild) observer.observe(box.firstElementChild);
    return () => {
      box.removeEventListener("scroll", read);
      observer.disconnect();
    };
  }, []);
  return { ref, more };
}

export function ApplicationsList({ applications }: { applications: Application[] }) {
  const { ref: edgeRef, more: moreToRight } = useMoreToRight();
  // The table scrolls inside its card, down to the page's foot, so the
  // search and the filters above stay in view (components/fill-page.ts).
  const fill = useFillPage();
  const query = useApplicationsQuery();
  const push = useShallowPush();
  const layout = useColumnLayout();
  const [drag, setDrag] = useState<{ id: ColumnId; over: ColumnId | null } | null>(null);

  const table = useTable({
    features: FEATURES,
    columns: COLUMN_DEFS,
    data: applications,
    getRowId: (app) => app.id,
    columnResizeMode: "onChange",
    state: {
      sorting: [{ id: SORT_COLUMN[query.sort], desc: SORT_DESC[query.sort] }],
      columnPinning: PINNING,
      columnOrder: [...FROZEN, ...layout.order],
      columnVisibility: Object.fromEntries(layout.hidden.map((id) => [id, false])),
      columnSizing: layout.widths as ColumnSizingState,
    },
    // The resize handles write here; the layout keeps it.
    onColumnSizingChange: (updater) => {
      const widths = typeof updater === "function" ? updater(layout.widths) : updater;
      setColumnLayout({ ...layout, widths: widths as ColumnLayout["widths"] });
    },
  });

  const lastFrozen = FROZEN[FROZEN.length - 1];

  /** A frozen column's sticky place, after the frozen columns before it:
   *  today Role alone, at the left edge. */
  function frozenStyle(id: ColumnId) {
    const column = table.getColumn(id);
    return column?.getIsPinned()
      ? ({ "--frozen-left": `${column.getStart("start")}px` } as CSSProperties)
      : undefined;
  }

  function frozenClasses(id: ColumnId) {
    return FROZEN.includes(id) && cn(FROZEN_CELL, id === lastFrozen && FROZEN_EDGE);
  }

  return (
    <Card ref={edgeRef} padding="none" className="relative mt-4 overflow-hidden">
      <span
        aria-hidden="true"
        className={cn(
          "from-panel pointer-events-none absolute inset-y-0 right-0 z-3 w-12 bg-linear-to-l to-transparent transition-opacity duration-200",
          moreToRight ? "opacity-100" : "opacity-0",
        )}
      />
      <Table
        containerRef={fill}
        containerClassName={TABLE_FILL}
        className="table-fixed"
        // At least as wide as the card; past that, as wide as its columns.
        style={{ width: table.getTotalSize(), minWidth: "100%" }}
      >
        <TableHeader>
          {table.getHeaderGroups().map((group) => (
            <TableRow key={group.id} className="hover:bg-transparent">
              {group.headers.map((header) => (
                <HeadCell
                  key={header.id}
                  header={header}
                  label={header.column.columnDef.header as string}
                  sort={query.sort}
                  onSort={(sort) => push(applicationsHref(query, { sort, app: null }))}
                  drag={drag}
                  onDrag={setDrag}
                  onDrop={(id, target) => setColumnLayout(moveColumn(layout, id, target))}
                  order={layout.order}
                  className={cn(
                    frozenClasses(header.column.id as ColumnId),
                    // Sticky on both axes: over the scrolled cells and the
                    // other headings.
                    FROZEN.includes(header.column.id as ColumnId) && "z-3",
                    header.column.id === "role" && PHONE_JOB,
                  )}
                  style={frozenStyle(header.column.id as ColumnId)}
                  centred={CENTRED.includes(header.column.id as ColumnId)}
                />
              ))}
              {/* The rest of the card's width, so a resize never stretches
                  the other columns. */}
              <TableHead aria-hidden />
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {table.getRowModel().rows.map((row, i) => (
            // Fades in down the table on arrival (a row cannot rise: its
            // transform does not reliably paint), 25ms apart, and glides to
            // its new place when the sort or a filter moves it.
            <Reflow key={row.id}>
              <ClickableRow
                href={applicationHref(row.id)}
                className="hover:bg-hover animate-fade"
                style={{ animationDelay: `${Math.min(i, 10) * 25}ms` }}
              >
                {row.getVisibleCells().map((cell) => {
                  const id = cell.column.id as ColumnId;
                  return (
                    <TableCell
                      key={cell.id}
                      // A click in the resume cell around View Resume is a
                      // near miss, not a wish to open the application:
                      // ClickableRow leaves a prevented click alone.
                      // The stage menu's cell too: its options open in a
                      // popup, whose clicks still reach the row in React.
                      onClick={
                        id === "status" || (id === "resume" && row.original.sentResume)
                          ? (event) => event.preventDefault()
                          : undefined
                      }
                      className={cn(
                        TD,
                        "overflow-hidden",
                        CENTRED.includes(id) && "text-center",
                        id === "role" && "py-3",
                        frozenClasses(id),
                        FROZEN.includes(id) && FROZEN_HOVER,
                      )}
                      style={frozenStyle(id)}
                    >
                      {CELL[id](row.original)}
                    </TableCell>
                  );
                })}
                <TableCell aria-hidden />
              </ClickableRow>
            </Reflow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

type Drag = { id: ColumnId; over: ColumnId | null } | null;

/**
 * One column heading: its label (a sort button where the column sorts), a
 * drag to move it, and a resize handle on its right edge.
 *
 * DRAGGING IS THE BROWSER'S OWN (HTML drag and drop) on the label, not the
 * whole cell, so a press on the resize handle never starts a move. While a
 * heading is dragged over another, a brand bar marks the side it will land
 * on. Frozen columns neither drag nor take a drop. A drag needs a mouse;
 * a phone keeps the default order, which the Columns menu can reset to.
 *
 * THE RESIZE HANDLE is 24px wide across the edge, a target the size the
 * rest of the table's controls are, with a 2px line (KAN-577; it was 8px).
 * It is TanStack's resize handler on mouse and touch, a
 * double click back to the default width, and the arrow keys for a
 * keyboard (a focusable separator with its width as its value). Its mouse
 * press cancels the browser's own default, and no move starts while a
 * column resizes: a resize moves the headings under a still-pressed
 * pointer, and Chrome then began a drag of the heading that slid under it,
 * which swallowed the mouse-up and left the resize following the pointer.
 */
function HeadCell({
  header,
  label,
  sort,
  onSort,
  drag,
  onDrag,
  onDrop,
  order,
  className,
  style,
  centred = false,
}: {
  header: Header<typeof FEATURES, Application, unknown>;
  label: string;
  sort: Sort;
  onSort: (sort: Sort) => void;
  drag: Drag;
  onDrag: (drag: Drag) => void;
  onDrop: (id: ColumnId, target: ColumnId) => void;
  order: ColumnId[];
  className?: string;
  style?: CSSProperties;
  /** A column of one control or score per row: its heading centred too. */
  centred?: boolean;
}) {
  const column = header.column;
  const id = column.id as ColumnId;
  const movable = !FROZEN.includes(id);
  const columnSort = COLUMN_SORT[id];
  const active = columnSort != null && sort === columnSort;
  const direction = columnSort ? (SORT_DESC[columnSort] ? "desc" : "asc") : undefined;
  const resize = header.getResizeHandler();
  const width = header.getSize();

  // Where the dragged column lands, beside this one.
  const over = drag != null && drag.over === id && drag.id !== id;
  const side = over && order.indexOf(drag.id) < order.indexOf(id) ? "right" : "left";

  function onKeyDown(event: KeyboardEvent) {
    const step = event.key === "ArrowLeft" ? -KEY_STEP : event.key === "ArrowRight" ? KEY_STEP : 0;
    if (!step) return;
    event.preventDefault();
    column.table.setColumnSizing((sizing) => ({
      ...sizing,
      [id]: Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width + step)),
    }));
  }

  const dragProps = movable
    ? {
        draggable: true,
        onDragStart: (event: DragEvent) => {
          if (column.table.getAllLeafColumns().some((other) => other.getIsResizing())) {
            event.preventDefault();
            return;
          }
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", id);
          onDrag({ id, over: null });
        },
        onDragEnd: () => onDrag(null),
      }
    : {};

  return (
    <TableHead
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : undefined}
      // Held at the top of the table's scroll box (STICKY_TH, positioned,
      // so the resize handle still sits on its edge).
      className={cn(TH, STICKY_TH, className)}
      style={{ width, ...style }}
      onDragOver={(event) => {
        if (!drag || !movable) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        if (drag.over !== id) onDrag({ ...drag, over: id });
      }}
      onDrop={(event) => {
        if (!drag || !movable) return;
        event.preventDefault();
        onDrop(drag.id, id);
        onDrag(null);
      }}
    >
      <div
        {...dragProps}
        className={cn(
          "flex min-w-0 items-center",
          centred && "justify-center",
          movable && "cursor-grab active:cursor-grabbing",
          drag?.id === id && "opacity-50",
        )}
      >
        {columnSort ? (
          <button
            type="button"
            onClick={() => onSort(columnSort)}
            title={SORT_HINT[columnSort]}
            className="hover:text-ink focus-visible:ring-brand-ring inline-flex min-h-6 min-w-0 items-center gap-1 rounded-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
          >
            <span className="truncate">{label}</span>
            {/* Keyed on its state, so the glyph pops in when the column
                takes the sort rather than swapping in place. */}
            <SortIcon
              key={active ? direction : "none"}
              className={cn(
                "animate-pop size-3.5 shrink-0",
                active ? "text-brand" : "text-ink-meta",
              )}
              direction={active ? direction : undefined}
            />
          </button>
        ) : (
          <span className="truncate">{label}</span>
        )}
      </div>

      {over && (
        <span
          aria-hidden
          className={cn(
            "bg-brand pointer-events-none absolute inset-y-1 w-0.5 rounded-full",
            side === "left" ? "left-0" : "right-0",
          )}
        />
      )}

      <div
        role="separator"
        aria-orientation="vertical"
        aria-label={`Resize ${label}`}
        aria-valuenow={width}
        aria-valuemin={MIN_WIDTH}
        aria-valuemax={MAX_WIDTH}
        tabIndex={0}
        title="Drag to resize, double-click to reset"
        onMouseDown={(event) => {
          event.preventDefault();
          resize(event);
        }}
        onTouchStart={resize}
        onDoubleClick={() => column.resetSize()}
        onKeyDown={onKeyDown}
        className={cn(
          "group/resize focus-visible:ring-brand-ring absolute inset-y-0 -right-3 z-2 flex w-6 cursor-col-resize touch-none justify-center select-none focus-visible:ring-2 focus-visible:outline-none",
        )}
      >
        <span
          className={cn(
            "h-full w-0.5 transition-colors",
            column.getIsResizing() ? "bg-brand" : "group-hover/resize:bg-border-control",
          )}
        />
      </div>
    </TableHead>
  );
}
