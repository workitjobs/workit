"use client";

import { TagIcon } from "@phosphor-icons/react/ssr";
import { useState } from "react";

import { AllFiltersBody, AllFiltersDialog, FilterSection } from "@/components/all-filters-dialog";
import { OptionChip as Chip, SearchPicker } from "@/components/filter-controls";
import { CompanyIcon } from "@/components/icons";
import { RESUME_TYPES, type ResumeType } from "@/components/resume-list";
import { RESUME_TYPE_ICON } from "@/components/resume-row";
import { RESUMES_GROUP_KEY } from "@/lib/local-drafts";
import { storedChoice } from "@/lib/stored-choice";

/**
 * Documents' resume filters beyond the row (2026-11-11), the same controls
 * the Tracker and Auto Apply's Up Next have (./built-resumes.tsx draws the
 * row): All Filters' panel, and Table Settings' Group By.
 *
 * GROUP BY Type or None, None by default: the list was grouped by type
 * from KAN-404 until 2026-11-10, when the user found the headings ugly
 * beside the grid, so it starts flat and the student can group it. The
 * headings are the shared quiet band (components/table-group.tsx), not the
 * old ones. The grid has no groups, and Table Settings shows with the list
 * only, as on the Tracker. A preference of this browser
 * (lib/stored-choice.ts).
 */
export const RESUME_GROUP_BY = [
  { value: "type", label: "Type" },
  { value: "none", label: "None" },
] as const;
export type ResumeGroupBy = (typeof RESUME_GROUP_BY)[number]["value"];

export const [useResumeGroupBy, setResumeGroupBy] = storedChoice<ResumeGroupBy>(
  RESUMES_GROUP_KEY,
  RESUME_GROUP_BY.map(({ value }) => value),
  "none",
);

export type ResumePicks = { types: ResumeType[]; companies: string[] };

/** All Filters for the resumes, in the shared panel
 *  (components/all-filters-dialog.tsx): Type as option chips, Company (a
 *  tailored resume's job posting's) as a search picker. `count` says how
 *  many resumes a draft shows, for "Show 6 Resumes". */
export function ResumeAllFilters({
  open,
  onOpenChange,
  picks,
  companies,
  count,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  picks: ResumePicks;
  companies: string[];
  count: (picks: ResumePicks) => number;
  onApply: (picks: ResumePicks) => void;
}) {
  return (
    <AllFiltersDialog open={open} onOpenChange={onOpenChange}>
      <PanelBody
        picks={picks}
        companies={companies}
        count={count}
        onApply={(next) => {
          onApply(next);
          onOpenChange(false);
        }}
      />
    </AllFiltersDialog>
  );
}

function PanelBody({
  picks,
  companies,
  count,
  onApply,
}: {
  picks: ResumePicks;
  companies: string[];
  count: (picks: ResumePicks) => number;
  onApply: (picks: ResumePicks) => void;
}) {
  const [draft, setDraft] = useState(picks);
  // Bumped by Clear All: the company picker keeps its search in its own
  // state, so it is remounted empty.
  const [cleared, setCleared] = useState(0);
  const shown = count(draft);

  return (
    <AllFiltersBody
      onClear={() => {
        setDraft({ types: [], companies: [] });
        setCleared((n) => n + 1);
      }}
      onShow={() => onApply(draft)}
      showLabel={`Show ${shown} ${shown === 1 ? "Resume" : "Resumes"}`}
    >
      <FilterSection Icon={TagIcon} label="Type" first>
        {RESUME_TYPES.map(({ value, label }) => (
          <Chip
            key={value}
            Icon={RESUME_TYPE_ICON[value]}
            pressed={draft.types.includes(value)}
            onClick={() =>
              setDraft((d) => ({
                ...d,
                // In the options' order, whatever order they were ticked in.
                types: RESUME_TYPES.map((t) => t.value).filter((v) =>
                  v === value ? !d.types.includes(v) : d.types.includes(v),
                ),
              }))
            }
          >
            {label}
          </Chip>
        ))}
      </FilterSection>

      <FilterSection Icon={CompanyIcon} label="Company">
        {companies.length === 0 ? (
          <p className="text-note text-ink-meta">
            No tailored resumes yet. Each one is for a job posting at a company.
          </p>
        ) : (
          <SearchPicker
            key={`company-${cleared}`}
            label="Companies"
            placeholder="Search a company"
            empty="No tailored resume for a company by that name."
            options={companies.map((value) => ({ value, label: value, nested: false }))}
            values={draft.companies}
            onChange={(values) => setDraft((d) => ({ ...d, companies: values }))}
          />
        )}
      </FilterSection>
    </AllFiltersBody>
  );
}
