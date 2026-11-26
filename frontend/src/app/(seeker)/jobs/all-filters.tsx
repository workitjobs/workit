"use client";

import { LightningRoundedIcon } from "@/components/custom-icons";
import { useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";

import {
  JobTypeIcon,
  CalendarIcon,
  ClockIcon,
  CoinIcon,
  LevelIcon,
  levelIcon,
  PinIcon,
  RoleIcon,
  VisaIcon,
  workStyleIcon,
} from "@/components/icons";
import {
  AllFiltersBody,
  AllFiltersDialog,
  AllFiltersSkeleton,
  FilterSection,
} from "@/components/all-filters-dialog";
import { OptionChip as Chip, SalaryPicker, SearchPicker } from "@/components/filter-controls";

import { countJobs } from "./actions";
import {
  addCustomRole,
  DATE_POSTED_OPTIONS,
  EXPERIENCE_OPTIONS,
  feedQuery,
  JOB_TYPE_OPTIONS,
  NO_FILTERS,
  PAY_OPTIONS,
  payUnits,
  roleOptions,
  roleValues,
  seasonLabel,
  splitRoleValues,
  statesNarrowCountries,
  VISA_OPTIONS,
  WORKPLACE_OPTIONS,
  type FeedFilters,
} from "./filter-query";
import type { JobFacets, JobLocationOption } from "./listings";

/**
 * ALL FILTERS IS ONE PANEL WITH EVERY OPTION IN VIEW (KAN-170), after
 * Airbnb's filters and LinkedIn's "All filters": a section per facet under
 * the glyph the job card draws for it, each option a chip. Options carry no
 * job count, as the row's don't (KAN-252); the button below counts the result.
 * It used to be a sheet of the row's dropdown buttons, which opened popups
 * inside a popup that landed left or right of their button depending on the
 * room. No popups in here.
 *
 * PICKS ARE A DRAFT UNTIL "SHOW 128 JOBS". The panel edits its own copy of
 * the filters; the feed is untouched until the button applies them, so a
 * dozen taps are one navigation, not a dozen. The button counts the draft as
 * it changes (GET /jobs/count through ./actions), so the seeker sees an empty
 * result before committing to it. Closing without it discards the draft.
 *
 * THE FRAME IS THE SHARED ONE (components/all-filters-dialog.tsx, KAN-823),
 * as on the Tracker, Up Next and Documents: the dialog, its sections, its
 * foot, and a skeleton while the places and roles load. This panel drew a
 * copy of that frame until then, with a "Loading the filters…" line.
 *
 * The body is mounted only while the panel is open, so each opening starts
 * from the filters the URL holds.
 */
export function AllFiltersPanel({
  open,
  onOpenChange,
  filters,
  locations,
  facets,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: FeedFilters;
  locations: Promise<JobLocationOption[]>;
  facets: Promise<JobFacets>;
  onApply: (filters: FeedFilters) => void;
}) {
  return (
    <AllFiltersDialog open={open} onOpenChange={onOpenChange}>
      {/* Seven sections, as many as the panel's first screen shows. */}
      <Suspense fallback={<AllFiltersSkeleton sections={7} />}>
        <PanelBody
          filters={filters}
          locations={locations}
          facets={facets}
          onApply={(next) => {
            onApply(next);
            onOpenChange(false);
          }}
        />
      </Suspense>
    </AllFiltersDialog>
  );
}

function PanelBody({
  filters,
  locations,
  facets,
  onApply,
}: {
  filters: FeedFilters;
  locations: Promise<JobLocationOption[]>;
  facets: Promise<JobFacets>;
  onApply: (filters: FeedFilters) => void;
}) {
  const places = use(locations);
  const facetOptions = use(facets);
  const [draft, setDraft] = useState(filters);
  // Bumped by Clear All: the pickers below keep what is typed in them (a
  // search, a salary figure) in their own state, so they are remounted empty.
  const [cleared, setCleared] = useState(0);
  const count = useDraftCount(draft);

  const set = (change: Partial<FeedFilters>) => setDraft((d) => ({ ...d, ...change }));

  return (
    <AllFiltersBody
      onClear={() => {
        setDraft(NO_FILTERS);
        setCleared((n) => n + 1);
      }}
      onShow={() => onApply(statesNarrowCountries(draft))}
      showLabel={
        count == null
          ? "Show Jobs"
          : `Show ${count.toLocaleString("en-US")} ${count === 1 ? "Job" : "Jobs"}`
      }
    >
      <FilterSection Icon={PinIcon} label="Location" first>
        <SearchPicker
          key={`places-${cleared}`}
          label="Places"
          placeholder="Search a state or country"
          empty="No place by that name has jobs."
          options={places.map((p) => ({
            value: p.code,
            label: p.label,
            nested: p.code.includes("-"),
          }))}
          values={draft.places}
          onChange={(next) => set({ places: next })}
        />
      </FilterSection>

      {/* Full width, as Location: its names are long, and the row puts it
            second. The job_roles that tag a job, in the database's order,
            from GET /jobs/facets (KAN-155). */}
      <FilterSection Icon={RoleIcon} label="Role">
        <SearchPicker
          key={`roles-${cleared}`}
          label="Roles"
          placeholder="Search a role"
          empty="No role by that name."
          // The student's own typed roles ride beside the listed ones
          // (filter-query's roleValues), and a role the list lacks can be
          // added from the search (2026-11-16).
          options={roleOptions(
            facetOptions.role.map((o) => ({ value: o.value, label: o.label, nested: false })),
            draft.customRoles,
          )}
          values={roleValues(draft)}
          onChange={(next) => set(splitRoleValues(next))}
          create={addCustomRole(draft.customRoles, (customRoles) => set({ customRoles }))}
        />
      </FilterSection>

      <div className="grid gap-x-6 sm:grid-cols-2">
        <FilterSection Icon={JobTypeIcon} label="Job Type">
          {JOB_TYPE_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              pressed={draft.jobTypes.includes(o.value)}
              onClick={() => set({ jobTypes: toggle(draft.jobTypes, o.value, JOB_TYPE_OPTIONS) })}
            >
              {o.label}
            </Chip>
          ))}
        </FilterSection>

        <FilterSection Icon={workStyleIcon("onsite")} label="Workplace">
          {WORKPLACE_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              Icon={workStyleIcon(o.value)}
              pressed={draft.workStyles.includes(o.value)}
              onClick={() =>
                set({ workStyles: toggle(draft.workStyles, o.value, WORKPLACE_OPTIONS) })
              }
            >
              {o.label}
            </Chip>
          ))}
        </FilterSection>

        <FilterSection Icon={LevelIcon} label="Experience Level">
          {EXPERIENCE_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              Icon={levelIcon(o.value)}
              pressed={draft.levels.includes(o.value)}
              onClick={() => set({ levels: toggle(draft.levels, o.value, EXPERIENCE_OPTIONS) })}
            >
              {o.label}
            </Chip>
          ))}
        </FilterSection>

        <FilterSection Icon={ClockIcon} label="Date Posted">
          <Chip pressed={draft.postedWithin == null} onClick={() => set({ postedWithin: null })}>
            Any Time
          </Chip>
          {DATE_POSTED_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              pressed={draft.postedWithin === o.value}
              onClick={() => set({ postedWithin: draft.postedWithin === o.value ? null : o.value })}
            >
              {o.label}
            </Chip>
          ))}
        </FilterSection>
      </div>

      <FilterSection Icon={CoinIcon} label="Salary">
        <SalaryPicker
          key={`pay-${cleared}`}
          units={payUnits(draft.jobTypes)}
          presets={PAY_OPTIONS}
          minPay={draft.minPay}
          maxPay={draft.maxPay}
          payPer={draft.payPer}
          onChange={(minPay, maxPay, payPer) => set({ minPay, maxPay, payPer })}
        />
      </FilterSection>

      <div className="grid gap-x-6 sm:grid-cols-2">
        <FilterSection Icon={CalendarIcon} label="Start Date">
          {facetOptions.start_term.length === 0 ? (
            <p className="text-note text-ink-meta">No start dates in the feed yet.</p>
          ) : (
            <SearchPicker
              key={`seasons-${cleared}`}
              label="Start Dates"
              placeholder="Search a season"
              empty="No season by that name has jobs."
              options={facetOptions.start_term.map((t) => ({
                value: t.value,
                label: seasonLabel(t.value),
              }))}
              values={draft.startTerms}
              onChange={(next) => set({ startTerms: next })}
            />
          )}
        </FilterSection>

        <FilterSection Icon={VisaIcon} label="Visa">
          {VISA_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              pressed={draft.visa === o.value}
              onClick={() => set({ visa: draft.visa === o.value ? null : o.value })}
            >
              {o.label}
            </Chip>
          ))}
        </FilterSection>
      </div>

      {/* Under the sidebar's Auto Apply glyph, as on a job's Auto Apply
            button. One chip: on, only the job postings that button shows
            on (Greenhouse for now); off, every job posting. */}
      <FilterSection Icon={LightningRoundedIcon} label="Auto Apply">
        <Chip pressed={draft.autoApply} onClick={() => set({ autoApply: !draft.autoApply })}>
          Auto Apply Supported
        </Chip>
      </FilterSection>
    </AllFiltersBody>
  );
}

/** The draft's job count, asked for a quarter second after the picks stop
 *  changing; the last one asked for wins. On /search it counts within the
 *  search's words (`?q`), as the results there are. Null while the current picks are
 *  being counted (the button says "Show Jobs" rather than the last picks'
 *  number, which a quick click would otherwise apply under), and when the
 *  API can't give one. */
function useDraftCount(draft: FeedFilters): number | null {
  const [answer, setAnswer] = useState<{ query: string; n: number | null } | null>(null);
  const query = feedQuery(draft, useSearchParams().get("q") ?? "");
  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      countJobs(query)
        .catch(() => null)
        .then((n) => {
          if (current) setAnswer({ query, n });
        });
    }, 250);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [query]);
  return answer?.query === query ? answer.n : null;
}

/** `values` with `value` added or removed, kept in the options' order. */
function toggle<T>(values: T[], value: T, options: readonly { value: T }[]): T[] {
  const next = values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
  return options.map((o) => o.value).filter((v) => next.includes(v));
}
