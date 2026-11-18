"use client";

import { usePathname, useRouter } from "next/navigation";
import { Suspense, use, useEffect, useOptimistic, useRef, useState, type ReactNode } from "react";

import { JobTypeIcon, ChevronDownIcon, PinIcon, RoleIcon, workStyleIcon } from "@/components/icons";
import { facetClasses, FacetLabel, FieldFacet, type FacetOption } from "@/components/field-facet";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/shadcn/popover";
import { SortMenu } from "@/components/sort-menu";
import { Button } from "@/components/ui/button";
import { CheckRowBox, checkRowClasses } from "@/components/ui/check-row";
import { AllFiltersButton, ClearFiltersButton } from "@/components/filter-actions";
import { cn } from "@/lib/cn";

import { SearchFacet } from "../applications/field-filters";
import {
  facetsOn,
  FILTER_KEYS,
  filterEntries,
  isFiltered,
  JOB_TYPE_OPTIONS,
  NO_FILTERS,
  WORKPLACE_OPTIONS,
  type FeedFilters,
  SORT_OPTIONS,
  sortHref,
  type Sort,
} from "./filter-query";
import { AllFiltersPanel } from "./all-filters";
import { useFeedTransition } from "./feed-transition";
import type { JobFacets, JobLocationOption } from "./listings";

/**
 * The filter row on /jobs and on /search, built from the filter parts every
 * page table shares (KAN-823), so it looks and acts as the Tracker's does:
 * `FieldFacet` (components/field-facet.tsx) for Workplace and Job Type, a
 * menu of checkbox rows; the Tracker's `SearchFacet` for Role, the same
 * button and rows with a search field over them (forty-odd roles were too
 * many to scroll through for one, KAN-252); and for Location a popover of
 * two panels (LocationFacet says why) on the same button (`facetClasses`,
 * `FacetLabel`) and the same rows (ui/check-row.tsx). Until KAN-823 the row
 * drew its own copies of that button, and each popup drew its rows its own
 * way. /search drew inert chips until it moved onto the live feed.
 *
 * EVERY FACET FILTERS, ON THE SERVER (KAN-170). Its picks are the page's
 * query (./filter-query owns the names, the options and the reading), so the
 * server fetches the feed narrowed to them and a reload or a shared link
 * keeps them. A pick replaces the URL rather than pushing it, so ticking five
 * boxes is not five steps of Back, and shows checked at once (useOptimistic)
 * while the narrowed feed is fetched. Each is a button that opens a list of
 * options. The button's own label never changes (a facet's picks show up as
 * checked items inside the popup, not as chips on the trigger), and the
 * trigger picks up a brand tint once a pick has been made and the popup has
 * closed, the one visible signal that a facet is in use. A screen reader hears
 * the same thing as the pick count after the label.
 *
 * EACH FACET WEARS ITS FACT'S GLYPH, the one the job card draws beside the
 * same fact (Location's pin, Salary's coin, Job Type's briefcase, Experience's
 * mortarboard), so the row and the card read as one vocabulary. Role, a fact
 * the card doesn't print, takes a person in a suit of its own.
 * Inside a popup an option has a glyph only where it differs by option:
 * Workplace's building, two arrows and house, exactly as the card picks them
 * (workStyleIcon), and, in All Filters, Experience Level's mortarboard and
 * check badge (levelIcon, KAN-252). The same briefcase on every Job Type row
 * would say nothing the button doesn't. Glyphs are ink, and brand once the
 * facet is in use, with its label.
 *
 * Job Type is what kind of job it is, Internship among them, and Experience
 * Level how much experience it asks for; they never overlap (KAN-284).
 * Experience's Student once meant exactly the internships, so Student with
 * Full-Time matched no job, and with Job Type in the panel only the seeker
 * never saw the pick that emptied the feed.
 */

/** "US" for "US-CA", and for "US" itself. */
const countryOf = (code: string) => code.split("-")[0];
const isState = (code: string) => code.includes("-");

/** The URL's places as the popup's ticks: a state ticks its country too. */
function ticksFrom(places: readonly string[]): string[] {
  return [...new Set(places.flatMap((code) => (isState(code) ? [countryOf(code), code] : [code])))];
}

/** The popup's ticks as the URL's places. A country alone means all of it; a
 *  country with states ticked means just those states. */
function placesFrom(ticks: readonly string[]): string[] {
  return ticks
    .filter((code) => !isState(code))
    .flatMap((country) => {
      const states = ticks.filter((code) => isState(code) && countryOf(code) === country);
      return states.length > 0 ? states : [country];
    });
}

/** One row of the Location popup: the check row every filter list draws
 *  (ui/check-row.tsx), as a real checkbox button. Its box answers to
 *  `data-checked`, as a menu's checkbox row's does. `current` marks the
 *  country whose states the other panel lists. */
function CheckRow({
  label,
  checked,
  current = false,
  onToggle,
}: {
  label: string;
  checked: boolean;
  current?: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      data-checked={checked ? "" : undefined}
      onClick={onToggle}
      className={cn(
        checkRowClasses,
        "hover:bg-accent focus-visible:bg-accent text-left",
        current && "bg-accent",
      )}
    >
      <span>{label}</span>
      <CheckRowBox />
    </button>
  );
}

/** A panel's small heading. */
function PanelHeading({ children }: { children: ReactNode }) {
  return <p className="text-note text-ink-meta px-2 pt-1 pb-1.5">{children}</p>;
}

/** Location once its options have arrived: a popover of two panels,
 *  countries on the left ("United States", "Other") and the states of the
 *  ticked country on the right. Ticking a country means all of it and opens
 *  its states beside it; ticking states narrows it to those. Unticking the
 *  country drops its states with it.
 *
 *  A Popover, not a `FieldFacet` like the other facets: a menu draws one
 *  list, and states nested in it read as one long dropdown. Its button and
 *  rows are the shared ones. `values` and `onChange` speak the URL's
 *  places, never the ticks. */
function LocationFacet({
  locations,
  values,
  onChange,
  className,
}: {
  locations: Promise<JobLocationOption[]>;
  values: string[];
  onChange: (values: string[]) => void;
  className?: string;
}) {
  const options = use(locations);
  const [open, setOpen] = useState(false);
  // The country whose states the right panel lists: the last one ticked
  // that has states, else the first ticked one that does.
  const [picked, setPicked] = useState<string | null>(null);

  const ticks = ticksFrom(values);
  const active = values.length > 0 && !open;
  const countries = options.filter(({ code }) => !isState(code));
  const statesOf = (country: string) =>
    options.filter(({ code }) => isState(code) && countryOf(code) === country);
  const hasStates = (country: string) => statesOf(country).length > 0;
  const shown =
    (picked != null && ticks.includes(picked) ? picked : null) ??
    countries.find(({ code }) => ticks.includes(code) && hasStates(code))?.code ??
    null;

  function toggleCountry(country: string) {
    if (ticks.includes(country)) {
      onChange(placesFrom(ticks.filter((code) => countryOf(code) !== country)));
    } else {
      if (hasStates(country)) setPicked(country);
      onChange(placesFrom([...ticks, country]));
    }
  }

  function toggleState(state: string) {
    onChange(
      placesFrom(
        ticks.includes(state) ? ticks.filter((code) => code !== state) : [...ticks, state],
      ),
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger disabled={options.length === 0} className={facetClasses(active, className)}>
        {/* The URL's places, not the ticks: picking California ticks the
            United States too, and should still say 1. */}
        <FacetLabel Icon={PinIcon} label="Location" active={active} count={values.length} />
        <ChevronDownIcon className="text-ink-meta size-4" />
      </PopoverTrigger>
      <PopoverContent
        align="start"
        aria-label="Location"
        className="w-auto max-w-[calc(100vw-2rem)] flex-col gap-0 p-1 sm:flex-row"
      >
        <div role="group" aria-label="Countries" className="flex min-w-40 flex-col">
          <PanelHeading>Country</PanelHeading>
          {countries.map(({ code, label }) => (
            <CheckRow
              key={code}
              label={label}
              checked={ticks.includes(code)}
              current={code === shown}
              onToggle={() => toggleCountry(code)}
            />
          ))}
        </div>

        <div className="bg-border my-1 h-px sm:mx-1 sm:my-0 sm:h-auto sm:w-px" />

        {/* Fixed width, so the popup keeps its size as countries are ticked
            and the states come and go. overscroll-none: a fling past the
            end of the states stops here instead of scrolling the page. */}
        <div className="flex w-full flex-col sm:w-56">
          <PanelHeading>State</PanelHeading>
          {shown == null ? (
            <p className="text-body text-ink-meta px-2 pb-2">
              Tick a country to narrow it by state.
            </p>
          ) : (
            <div
              role="group"
              aria-label={`States in ${countries.find(({ code }) => code === shown)?.label}`}
              className="flex max-h-72 flex-col overflow-y-auto overscroll-none"
            >
              {statesOf(shown).map(({ code, label }) => (
                <CheckRow
                  key={code}
                  label={label}
                  checked={ticks.includes(code)}
                  onToggle={() => toggleState(code)}
                />
              ))}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

/** Location's facet, standing disabled in its own place until the options
 *  arrive, so the row paints at once and nothing moves when they land. */
function Location(props: Parameters<typeof LocationFacet>[0]) {
  const active = props.values.length > 0;
  return (
    <Suspense
      fallback={
        <button type="button" disabled className={facetClasses(active, props.className)}>
          <FacetLabel Icon={PinIcon} label="Location" active={active} count={props.values.length} />
          <ChevronDownIcon className="text-ink-meta size-4" />
        </button>
      }
    >
      <LocationFacet {...props} />
    </Suspense>
  );
}

type RoleProps = {
  values: string[];
  onChange: (values: string[]) => void;
  className?: string;
};

/** Role's button and search, whether its options have loaded or not. */
function RoleSearch({ roles, ...props }: RoleProps & { roles: JobFacets["role"] }) {
  const names = new Map(roles.map((r) => [r.value, r.label]));
  return (
    <SearchFacet
      label="Role"
      Icon={RoleIcon}
      searchLabel="Search roles"
      empty="No role by that name."
      options={roles.map((r) => r.value)}
      labelOf={(value) => names.get(value) ?? value}
      {...props}
    />
  );
}

/** Role once GET /jobs/facets has answered: the `job_roles` that tag a job,
 *  in the database's order (KAN-155). Its options come from there, so unlike
 *  the other facets it waits on them, as Location waits on its places,
 *  standing disabled (no options) in its place meanwhile. */
function RoleFacet({ facets, ...props }: RoleProps & { facets: Promise<JobFacets> }) {
  return (
    <Suspense fallback={<RoleSearch roles={[]} {...props} />}>
      <RoleOptions facets={facets} {...props} />
    </Suspense>
  );
}

function RoleOptions({ facets, ...props }: RoleProps & { facets: Promise<JobFacets> }) {
  return <RoleSearch roles={use(facets).role} {...props} />;
}

/** A facet's fixed options as the dropdown's. */
function optionsOf(options: readonly { value: string | number; label: string }[]): FacetOption[] {
  return options.map((o) => ({ value: String(o.value), label: o.label }));
}

const hasPlaces = (places: JobLocationOption[]) => places.length > 0;
const hasFacets = (facets: JobFacets) => facets.work_style.length > 0;

/** The first of a series of promises that resolves with data, held from then
 *  on; until one has, the latest. The row's places and roles don't change
 *  with the filters, so once they've loaded, the promise each later render
 *  hands down would only re-suspend Location and Role while the same lists
 *  load again. But a first load that failed (the API down, an
 *  empty answer) mustn't stick for the visit: Next caches only good answers,
 *  so a later render's promise is worth taking until one comes back filled. */
function useHeldOnceFilled<T>(latest: Promise<T>, filled: (value: T) => boolean): Promise<T> {
  const [held, setHeld] = useState(latest);
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    if (settled) return;
    let alive = true;
    held.then((value) => {
      if (!alive) return;
      if (filled(value)) setSettled(true);
      else if (latest !== held) setHeld(latest);
    });
    return () => {
      alive = false;
    };
  }, [held, latest, settled, filled]);
  return held;
}

/** The facet row plus the All Filters panel (./all-filters), which holds every
 *  facet, and Salary, Start Date and Visa, which the row leaves to it.
 *  `locations` is the Location facet's options, still loading; `filters` the
 *  picks the page was opened with (./filter-query). */
export function JobFilters({
  locations: locationsLoading,
  facets: facetsLoading,
  filters,
  sort,
  list,
}: {
  locations: Promise<JobLocationOption[]>;
  /** GET /jobs/facets: the Role and Start Date options, still loading. */
  facets: Promise<JobFacets>;
  filters: FeedFilters;
  /** The Jobs page's order, for the row's Sort. /search has one order. */
  sort?: Sort;
  /** The list these filters narrow, when the row sits on a job's page beside
   *  it (./jobs-rail.tsx): a pick then goes to that list, not this address. */
  list?: { path: string; query: string };
}) {
  const [allFiltersOpen, setAllFiltersOpen] = useState(false);
  // Clear Filters leaves with the last pick, so its press hands focus here.
  const allFiltersButton = useRef<HTMLButtonElement>(null);
  // The first page's places and roles, kept for as long as the row is on
  // screen. They don't depend on the filters, so the promises each filter
  // change's render hands down again would only re-suspend Location and Role
  // while the same lists load a second time.
  const locations = useHeldOnceFilled(locationsLoading, hasPlaces);
  const facets = useHeldOnceFilled(facetsLoading, hasFacets);
  const startFeedTransition = useFeedTransition();
  const router = useRouter();
  const here = usePathname();
  const pathname = list?.path ?? here;
  // The picks show checked at once; `filters` catches up when the narrowed
  // page arrives.
  const [shown, show] = useOptimistic(filters);
  const [shownSort, showSort] = useOptimistic(sort);

  /** Moves the URL's filters to these, keeping the rest of the query (?q on
   *  /search). The server draws the feed again, narrowed.
   *
   *  ONE BACK RULE (KAN-916): a filter and a sort both replace the address,
   *  so Back leaves the list for the page before it, whatever was picked on
   *  it. The sort pushed until then, so Back stepped through each order but
   *  skipped every filter, and a student could not tell what Back would undo. */
  function apply(next: FeedFilters) {
    // The feed's transition, so the list dims the moment this starts
    // (./feed-transition).
    startFeedTransition(() => {
      show(next);
      const query = new URLSearchParams(list?.query ?? window.location.search);
      for (const key of FILTER_KEYS) query.delete(key);
      for (const [key, value] of filterEntries(next)) query.append(key, value);
      let search = query.toString();
      // Bare /jobs is a fresh visit, which the page sends on to the saved
      // preferences, so a cleared row with no ?sort (as Home's
      // week and month links open it) names the default order instead.
      if (!search && pathname === "/jobs") search = "sort=match";
      router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false });
    });
  }

  /** The list in this order, under the filters as they stand. */
  function applySort(next: Sort) {
    startFeedTransition(() => {
      showSort(next);
      router.replace(sortHref(next, shown), { scroll: false });
    });
  }

  const filtered = isFiltered(shown);
  const on = facetsOn(shown);

  /** One facet's change, the others as they stand. */
  const set = (change: Partial<FeedFilters>) => apply({ ...shown, ...change });

  // The row's facets, each given the width classes its place in the row needs.
  const facet = {
    // The job_roles that tag a job (KAN-155), from GET /jobs/facets, found
    // by typing here as in the panel's search picker (KAN-252).
    role: (className: string) => (
      <RoleFacet
        facets={facets}
        values={shown.roles}
        onChange={(roles) => set({ roles })}
        className={className}
      />
    ),
    workplace: (className: string) => (
      <FieldFacet
        Icon={workStyleIcon("onsite")}
        label="Workplace"
        options={optionsOf(WORKPLACE_OPTIONS).map((o) => ({
          ...o,
          Icon: workStyleIcon(o.value),
        }))}
        values={shown.workStyles}
        onChange={(values) => set({ workStyles: values as FeedFilters["workStyles"] })}
        className={className}
      />
    ),
    jobType: (className: string) => (
      <FieldFacet
        Icon={JobTypeIcon}
        label="Job Type"
        options={optionsOf(JOB_TYPE_OPTIONS)}
        values={shown.jobTypes}
        onChange={(values) => set({ jobTypes: values as FeedFilters["jobTypes"] })}
        className={className}
      />
    ),
    location: (className: string) => (
      <Location
        locations={locations}
        values={shown.places}
        onChange={(places) => set({ places })}
        className={className}
      />
    ),
  };

  return (
    <>
      {/* THE FACETS STEP OUT ONE AT A TIME, least used first, from the right,
          and All Filters stays at every width, a 36px icon named by its
          tooltip (KAN-519; components/filter-actions.tsx, shared with the
          Tracker since 2026-11-10). Each facet is at least 144px and as wide
          as its label needs, Clear (a text button with a cross) about 70,
          with 8px gaps, so the row fits them on one line from these widths of
          row (the page's @container, so an open sidebar or Scout counts): on
          /search Location and All Filters anywhere, then Role from 428px,
          Workplace 580 and Job Type 740, each a few pixels over what it needs,
          for a
          label that renders a little wider elsewhere. Those leave room for
          Clear Filters whether or not it shows, so a pick never pushes a
          facet out of the row or All Filters onto a second line (KAN-252).
          Job Type took Experience's place (KAN-284):
          it is where Internship is picked, and a pick out of sight emptied
          the feed (Student with Full-Time). Experience Level is in the panel
          only; until the scraper keeps experienced roles, its Entry Level
          matches every job.
          Role sits second, beside Location (KAN-171): with every field in
          one feed (KAN-172), which kind of role is the first thing a
          seeker narrows by, and software and engineering are half of it
          (1,660 of 3,507 job postings on 2026-10-10), so a marketing or
          design seeker otherwise scrolls past them all. Visa is in the
          panel only (asked for 2026-10-10), and so is Date Posted (2026-11-02),
          which left the row for the room. The row used to drop all its facets at once below 896px and stretch All
          Filters across the row, which on a laptop with the sidebar open
          left one wide bar where four filters had fit. The panel holds
          every facet, and Salary, Start Date and Date Posted, which the row has no
          room for. */}
      {/* Sort is always in the row, first, so on the Jobs page each facet steps
          out one place sooner: Sort takes Location's place on a phone. */}
      {shownSort && (
        <SortMenu
          value={shownSort}
          options={SORT_OPTIONS}
          onChange={applySort}
          className="min-w-36"
        />
      )}
      {sort ? (
        <>
          {facet.location("hidden min-w-36 @min-[26.75rem]:flex")}
          {facet.role("hidden min-w-36 @min-[36.25rem]:flex")}
          {facet.workplace("hidden min-w-36 @min-[46.25rem]:flex")}
          {facet.jobType("hidden min-w-36 @min-[55.75rem]:flex")}
        </>
      ) : (
        <>
          {facet.location("min-w-36")}
          {facet.role("hidden min-w-36 @min-[26.75rem]:flex")}
          {facet.workplace("hidden min-w-36 @min-[36.25rem]:flex")}
          {facet.jobType("hidden min-w-36 @min-[46.25rem]:flex")}
        </>
      )}

      {/* Every pick off in one press (KAN-252), shown only while there is
          one: the panel's Clear All, without opening the panel. "Clear"
          with a cross, a text button (components/filter-actions.tsx); it
          was a round soft-grey X named by its tooltip, and before that the
          words "Clear Filters" (93px), which cost the row a facet. It keeps
          ?sort and ?q as every pick does, and apply() keeps /jobs off the
          bare URL, so the list stays cleared rather than bringing the saved
          preferences back. The press hands focus to All Filters,
          since the button leaves with the last pick. */}
      {filtered && (
        <ClearFiltersButton
          className="animate-fade ml-auto shrink-0"
          onClick={() => {
            allFiltersButton.current?.focus();
            apply(NO_FILTERS);
          }}
        />
      )}
      {/* Clear and All Filters as on the Tracker (components/
          filter-actions.tsx, 2026-11-10): in words, not round icons named
          by their tooltips. Its count is the facets with a pick (KAN-569):
          below about 1000px of row some facets have stepped out, and their
          picks showed nowhere else. */}
      <AllFiltersButton
        ref={allFiltersButton}
        count={on}
        onClick={() => setAllFiltersOpen(true)}
        className={cn("shrink-0", !filtered && "ml-auto")}
      />

      <AllFiltersPanel
        open={allFiltersOpen}
        onOpenChange={setAllFiltersOpen}
        filters={shown}
        locations={locations}
        facets={facets}
        onApply={apply}
      />
    </>
  );
}

/** Clear Filters on the Jobs page's no-results state (KAN-823), as on Up
 *  Next's and Documents': every pick off, as the row's Clear does. It keeps
 *  the order and replaces the address, as a pick does, in the feed's
 *  transition, so the state dims the moment it is pressed. The address is
 *  `sortHref`'s, the one the row's Clear lands on (./canonical-url says
 *  why the two must agree). */
export function ClearFeedFilters({ sort }: { sort: Sort }) {
  const startFeedTransition = useFeedTransition();
  const router = useRouter();
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() =>
        startFeedTransition(() => router.replace(sortHref(sort, NO_FILTERS), { scroll: false }))
      }
    >
      Clear Filters
    </Button>
  );
}
