"use client";

import { createContext, use, type ReactNode } from "react";

import type { ApplicationStage } from "../auto-apply/actions";
import type { JobFacets, JobLocationOption } from "./listings";

/**
 * What the Jobs page reads once per visit (KAN-916): everything its list
 * needs that no filter, sort or view changes. Read in a layout, which Next
 * does not draw again when only the address's query changes, so a filter or
 * sort change asks the API for its list alone. They were read in the page,
 * and each change asked for them again: 8 API calls in the Card View, of
 * which only the list depended on the filters, and about 14 in the Split View
 * (2026-11-18). The promises resolve once; a later change reads them at once.
 *
 * TWO LAYOUTS, TWO CONTEXTS. The filter row's options are the jobs layout's
 * (../layout.tsx), since the split view's header stays drawn beside a job's
 * page too. The rest is /jobs's own ((list)/layout.tsx), so a job's page
 * opened from Home or the Tracker reads none of it.
 *
 * Stale within a visit on purpose: a stage set in this tab is laid over the
 * stages read (`drawnAt`, ./feed-stages), a tailored resume saves its job,
 * which leaves the list, and a `router.refresh()` reads them all again.
 */
export type FilterOptions = {
  locations: Promise<JobLocationOption[]>;
  facets: Promise<JobFacets>;
};

export type ListData = {
  /** Each job's application stage, read once (getApplicationStages). */
  stages: Promise<Record<string, ApplicationStage>>;
  /** The job ids the seeker has a tailored resume for. */
  tailored: Promise<string[]>;
  /** An applicant, whom a card's Apply Now may ask "Did You Apply?". */
  canMarkApplied: Promise<boolean>;
  /** When `stages` was read (ms): the seeker's changes since win. */
  drawnAt: number;
  /** The empty bank's prompt (./bank-prompt), streamed in its own boundary. */
  bankPrompt: ReactNode;
};

const FilterOptionsContext = createContext<FilterOptions | null>(null);
const ListDataContext = createContext<ListData | null>(null);

export function FilterOptionsProvider({
  locations,
  facets,
  children,
}: FilterOptions & { children: ReactNode }) {
  return <FilterOptionsContext value={{ locations, facets }}>{children}</FilterOptionsContext>;
}

export function ListDataProvider({
  stages,
  tailored,
  canMarkApplied,
  drawnAt,
  bankPrompt,
  children,
}: ListData & { children: ReactNode }) {
  return (
    <ListDataContext value={{ stages, tailored, canMarkApplied, drawnAt, bankPrompt }}>
      {children}
    </ListDataContext>
  );
}

/** The filter row's options, from the jobs layout. */
export function useFilterOptions(): FilterOptions {
  const options = use(FilterOptionsContext);
  if (!options) throw new Error("useFilterOptions needs the jobs layout");
  return options;
}

/** /jobs's per-visit reads, from its layout. */
export function useListData(): ListData {
  const data = use(ListDataContext);
  if (!data) throw new Error("useListData needs /jobs's layout");
  return data;
}

/** The tailored job ids when drawn under /jobs, else null: a job's own page,
 *  which reads its own (./[jobId]/job-view.tsx). */
export function useTailoredIds(): string[] | null {
  const data = use(ListDataContext);
  return data ? use(data.tailored) : null;
}
