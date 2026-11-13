"use client";

import { SELECTION_ROW } from "@/components/selection-bar";
import { ClockIcon, PencilLineIcon, ProhibitIcon } from "@phosphor-icons/react/ssr";
import { useRef, useState, type ReactNode } from "react";

import { AllFiltersBody, AllFiltersDialog, FilterSection } from "@/components/all-filters-dialog";
import { FieldFacet, type FacetOption } from "@/components/field-facet";
import { AllFiltersButton, ClearFiltersButton } from "@/components/filter-actions";
import { OptionChip as Chip, SearchPicker } from "@/components/filter-controls";
import { MatchIcon } from "@/components/icons";
import { GroupByOptions, TableSettingsMenu } from "@/components/table-settings";
import { PAGE_SEARCH, SearchField } from "@/components/ui/search-field";
import { cn } from "@/lib/cn";

import { FIELD_ICON, SearchFacet } from "../applications/field-filters";
import { StatusIcon } from "../applications/icons";
import { QUEUE_GROUP_BY, setQueueGroupBy, useQueueGroupBy } from "./queue-layout";
import { MATCH_KEYS, matchKey, type QueueGroup, type QueueRow } from "./queue-table";

/**
 * Up Next's toolbar (2026-11-10): the Tracker's, row for row, so the page
 * tables read alike (applications/filter-bar.tsx, resumes/built-resumes.tsx).
 *
 *   1. The search over job and company, with the page's actions at its
 *      right (`actions`: Add Jobs, or what to do to the picked rows), where
 *      the Tracker has its view switch and Documents Upload and Generate.
 *   2. A dropdown each for Status, Company and Match, then, at the right,
 *      Clear (while anything is searched or picked), All Filters (a panel
 *      with every one of them, `QueueAllFilters`) and Table Settings, which
 *      holds Group By (components/table-settings.tsx, ./queue-layout.ts).
 *
 * It was one row for a day (2026-11-10), the search beside the dropdowns
 * under an "Up Next" heading that held Add Jobs: the user found it unlike
 * the other two tables, so the heading went and the search took the
 * Tracker's own row (2026-11-11). With nothing queued, only the actions
 * show: there is nothing to search or filter.
 *
 * IN THE PAGE, NOT THE URL. Up Next holds every queued job already, so the
 * rows are filtered here as the student types or picks, with nothing sent;
 * the picks last while the page is open (a refresh after a batch keeps
 * them). The Tracker's ride in its URL because its server filters them.
 */
export type QueueFilters = {
  q: string;
  groups: QueueGroup[];
  companies: string[];
  /** Match bands by name (`matchKey`). */
  match: string[];
};

export const NO_QUEUE_FILTERS: QueueFilters = { q: "", groups: [], companies: [], match: [] };

/** Status's options: Up Next's groups, in its order, with the glyph each
 *  row's status draws when no heading names it. */
const STATUS_OPTIONS: (FacetOption & { value: QueueGroup })[] = [
  { value: "progress", label: "In Progress", Icon: PencilLineIcon, iconClassName: "text-advanced" },
  { value: "queued", label: "Queued", Icon: ClockIcon, iconClassName: "text-ink-meta" },
  { value: "closed", label: "Posting Closed", Icon: ProhibitIcon, iconClassName: "text-ink" },
];

/** A band's colour, as the match ring draws it (lib/match.ts). */
const MATCH_INK: Record<string, string> = {
  "Excellent Match": "text-match-excellent",
  "Good Match": "text-match-good",
  "Fair Match": "text-match-fair",
  "Weak Match": "text-match-weak",
};

/** A dot in the band's colour, where an option's glyph goes. */
function BandDot({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className}>
      <circle cx="8" cy="8" r="4" fill="currentColor" />
    </svg>
  );
}

const MATCH_OPTIONS: FacetOption[] = MATCH_KEYS.map((key) => ({
  value: key,
  label: key,
  Icon: BandDot,
  // Not Scored's dot is faint, so the labels line up.
  iconClassName: MATCH_INK[key] ?? "text-ink-faint",
}));

/** How many values are picked, for All Filters' badge. */
function pickCount(filters: QueueFilters) {
  return filters.groups.length + filters.companies.length + filters.match.length;
}

/** The rows `filters` let through, in their order. */
export function filterQueue(rows: QueueRow[], filters: QueueFilters) {
  const q = filters.q.trim().toLowerCase();
  return rows.filter(
    (row) =>
      (q === "" || row.role.toLowerCase().includes(q) || row.company.toLowerCase().includes(q)) &&
      (filters.groups.length === 0 || filters.groups.includes(row.group)) &&
      (filters.companies.length === 0 || filters.companies.includes(row.company)) &&
      (filters.match.length === 0 || filters.match.includes(matchKey(row.match))),
  );
}

/** Whether anything is searched or picked, so Clear shows. */
export function isFiltered(filters: QueueFilters) {
  return filters.q !== "" || pickCount(filters) > 0;
}

export function QueueToolbar({
  rows,
  filters,
  onChange,
  actions,
  selection,
}: {
  /** Every row, filtered or not: the Company options and the panel's count. */
  rows: QueueRow[];
  filters: QueueFilters;
  onChange: (filters: QueueFilters) => void;
  /** The search row's right end. */
  actions: ReactNode;
  /** The picked rows' bar, laid over the filter row
   *  (components/selection-bar.tsx). */
  selection?: ReactNode;
}) {
  const groupBy = useQueueGroupBy();
  const [allOpen, setAllOpen] = useState(false);
  // Clear leaves with the last pick, so its press hands focus here.
  const allButton = useRef<HTMLButtonElement>(null);
  const companies = [...new Set(rows.map((row) => row.company))].sort((a, b) => a.localeCompare(b));
  const filtered = isFiltered(filters);

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        {rows.length > 0 && (
          <SearchField
            id="queue-search"
            label="Search Up Next"
            placeholder="Search job or company"
            value={filters.q}
            onChange={(event) => onChange({ ...filters, q: event.target.value })}
            enterKeyHint="search"
            className={PAGE_SEARCH}
          />
        )}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">{actions}</div>
      </div>

      {/* THE DROPDOWNS STEP OUT ONE AT A TIME, from the right, at the
          Tracker's own widths for its first three (Status from 440px of
          row, Company 592, Match 744); All Filters, which holds them all,
          stays at every width. A phone's row is All Filters and Table
          Settings. */}
      {rows.length > 0 && (
        <div className={cn("@container mt-3 flex items-center gap-2", SELECTION_ROW)}>
          {selection}
          <FieldFacet
            label="Status"
            Icon={StatusIcon}
            options={STATUS_OPTIONS}
            values={filters.groups}
            onChange={(groups) => onChange({ ...filters, groups: groups as QueueGroup[] })}
            className="hidden min-w-36 @min-[27.5rem]:flex"
          />
          <SearchFacet
            label="Company"
            Icon={FIELD_ICON.company}
            searchLabel="Search companies"
            empty="No company by that name."
            options={companies}
            values={filters.companies}
            onChange={(values) => onChange({ ...filters, companies: values })}
            className="hidden min-w-36 @min-[37rem]:flex"
          />
          <FieldFacet
            label="Match"
            Icon={MatchIcon}
            options={MATCH_OPTIONS}
            values={filters.match}
            onChange={(match) => onChange({ ...filters, match })}
            className="hidden min-w-36 @min-[46.5rem]:flex"
          />

          {filtered && (
            <ClearFiltersButton
              className="animate-fade ml-auto shrink-0"
              onClick={() => {
                allButton.current?.focus();
                onChange(NO_QUEUE_FILTERS);
              }}
            />
          )}
          <AllFiltersButton
            ref={allButton}
            count={pickCount(filters)}
            onClick={() => setAllOpen(true)}
            className={cn("shrink-0", !filtered && "ml-auto")}
          />
          <TableSettingsMenu>
            <GroupByOptions options={QUEUE_GROUP_BY} value={groupBy} onChange={setQueueGroupBy} />
          </TableSettingsMenu>
        </div>
      )}

      <QueueAllFilters
        open={allOpen}
        onOpenChange={setAllOpen}
        rows={rows}
        companies={companies}
        filters={filters}
        onApply={onChange}
      />
    </>
  );
}

/**
 * All Filters for Up Next, in the shared panel
 * (components/all-filters-dialog.tsx): Status and Match as option chips,
 * Company as a search picker. "Show 4 Jobs" counts the draft.
 */
function QueueAllFilters({
  open,
  onOpenChange,
  rows,
  companies,
  filters,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rows: QueueRow[];
  companies: string[];
  filters: QueueFilters;
  onApply: (filters: QueueFilters) => void;
}) {
  return (
    <AllFiltersDialog open={open} onOpenChange={onOpenChange}>
      <PanelBody
        rows={rows}
        companies={companies}
        filters={filters}
        onApply={(next) => {
          onApply(next);
          onOpenChange(false);
        }}
      />
    </AllFiltersDialog>
  );
}

function PanelBody({
  rows,
  companies,
  filters,
  onApply,
}: {
  rows: QueueRow[];
  companies: string[];
  filters: QueueFilters;
  onApply: (filters: QueueFilters) => void;
}) {
  const [draft, setDraft] = useState(filters);
  // Bumped by Clear All: the company picker keeps its search in its own
  // state, so it is remounted empty.
  const [cleared, setCleared] = useState(0);
  const count = filterQueue(rows, draft).length;

  /** `value` ticked or unticked, the list kept in the options' order. */
  function toggle<K extends "groups" | "match">(key: K, value: string, order: readonly string[]) {
    setDraft((d) => {
      const now = d[key] as string[];
      const next = now.includes(value) ? now.filter((v) => v !== value) : [...now, value];
      return { ...d, [key]: order.filter((v) => next.includes(v)) };
    });
  }

  return (
    <AllFiltersBody
      onClear={() => {
        setDraft({ ...NO_QUEUE_FILTERS, q: draft.q });
        setCleared((n) => n + 1);
      }}
      onShow={() => onApply(draft)}
      showLabel={`Show ${count} ${count === 1 ? "Job" : "Jobs"}`}
    >
      <FilterSection Icon={StatusIcon} label="Status" first>
        {STATUS_OPTIONS.map((option) => (
          <Chip
            key={option.value}
            Icon={option.Icon}
            pressed={draft.groups.includes(option.value)}
            onClick={() =>
              toggle(
                "groups",
                option.value,
                STATUS_OPTIONS.map((o) => o.value),
              )
            }
          >
            {option.label}
          </Chip>
        ))}
      </FilterSection>

      <FilterSection Icon={FIELD_ICON.company} label="Company">
        <SearchPicker
          key={`company-${cleared}`}
          label="Companies"
          placeholder="Search a company"
          empty="No company by that name in Up Next."
          options={companies.map((value) => ({ value, label: value, nested: false }))}
          values={draft.companies}
          onChange={(values) => setDraft((d) => ({ ...d, companies: values }))}
        />
      </FilterSection>

      <FilterSection Icon={MatchIcon} label="Match">
        {MATCH_KEYS.map((key) => (
          <Chip
            key={key}
            pressed={draft.match.includes(key)}
            onClick={() => toggle("match", key, MATCH_KEYS)}
          >
            {key}
          </Chip>
        ))}
      </FilterSection>
    </AllFiltersBody>
  );
}
