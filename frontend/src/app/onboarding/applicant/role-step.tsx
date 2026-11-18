"use client";

import { useState, type ComponentType, type ReactNode } from "react";

import {
  addCustomRole,
  EXPERIENCE_OPTIONS,
  JOB_TYPE_OPTIONS,
  PAY_OPTIONS,
  payUnits,
  roleOptions,
  roleValues,
  splitRoleValues,
  WORKPLACE_OPTIONS,
  type FeedFilters,
} from "@/app/(seeker)/jobs/filter-query";
import { SalaryPicker, SearchPicker, type PickOption } from "@/components/filter-controls";
import { Button } from "@/components/ui/button";
import { ChoiceTile } from "@/components/ui/choice-tile";
import { Chip } from "@/components/ui/chip";
import { SegmentedToggle } from "@/components/ui/segmented-control";
import { TextField } from "@/components/ui/text-field";
import {
  JobTypeIcon,
  CalendarIcon,
  ClockIcon,
  CoinIcon,
  LevelIcon,
  PinIcon,
  RoleIcon,
  workStyleIcon,
} from "@/components/icons";
import { cn } from "@/lib/cn";

import { formatPay, payAmount } from "./pay-format";
import { SearchDialog } from "./search-dialog";

/**
 * The job preferences' controls, and the Field each question sits in. Its
 * own module because two screens draw them: the wizard (./onboarding-form),
 * one question or two per page with each control on its own (`RolePicker`,
 * `JobTypeChoices` ...), and Settings' Job Preferences (KAN-326), which
 * draws every one at once in its Field (`RoleStep`), `dense`. One set of
 * controls, so the two cannot ask different questions.
 *
 * `dense` IS SETTINGS' SIZE, NOT ONBOARDING'S SHRUNK. Onboarding draws each
 * question large on purpose: it is the whole screen, one step at a time.
 * Settings is one section of a modal among others, so `dense` draws what
 * the rest of the app draws for the same choices: 14px headings with a
 * 16px glyph, the pickers at their default 42px, and the answers as the
 * Jobs page's filter chips (`Choices`) in place of 56px tiles. Until
 * 2026-11-03 it only shrank the headings, and the section read as
 * onboarding dropped into Settings.
 *
 * ONE MARK: a red * on the three answers Save and Next need, and nothing on
 * the four optional ones (`tag={false}`), as every form with a required
 * field in the app marks it (ui/text-field.tsx's RequiredMark; Settings'
 * Personal Details beside it). It marked both ways, * and "Optional", until
 * KAN-829. "Optional" stays for a step with no required question, once.
 */

type Glyph = ComponentType<{ className?: string }>;

const toggle = <T,>(values: T[], value: T) =>
  values.includes(value) ? values.filter((v) => v !== value) : [...values, value];

export type StepProps = { answers: FeedFilters; set: (change: Partial<FeedFilters>) => void };

/** One question's control on its own, with no heading: the wizard's
 *  one-question pages draw them under the page's h1 (./onboarding-form),
 *  and RoleStep below wraps each in its Field. `labelledBy` names a group of
 *  tiles where no Field section does. */
type PieceProps = StepProps & { dense?: boolean; labelledBy?: string };

export function RolePicker({
  answers,
  set,
  roles,
  dense = false,
}: PieceProps & { roles: PickOption[] }) {
  return (
    <SearchPicker
      size={dense ? "default" : "lg"}
      label="Roles"
      placeholder="Search a role, or type your own"
      empty="No role by that name."
      // The student's own typed roles beside the listed ones, and a role
      // the list lacks added from the search (2026-11-16).
      options={roleOptions(roles, answers.customRoles)}
      values={roleValues(answers)}
      onChange={(next) => set(splitRoleValues(next))}
      create={addCustomRole(answers.customRoles, (customRoles) => set({ customRoles }))}
    />
  );
}

/**
 * The roles onboarding's Role page shows as tiles, in order, by `job_roles`
 * slug: picked by hand (2026-11-16), for the students WorkIt serves. Each
 * main group of students (CS, data, product, business and finance, the
 * classic engineering majors) finds its role in one click, and each has
 * enough postings that a first feed is not empty. The eight with the most
 * postings were tried first and read wrong: Sales Representative (1,271) and
 * Nurse (826) are posted in bulk, but no student had picked either, while 13
 * of 22 saved profiles picked Software Engineer and 8 AI/ML Engineer. Revisit
 * by what students pick once a few hundred have signed up. A slug the API
 * no longer lists is skipped.
 */
const POPULAR_ROLES = [
  "software_engineer",
  "ai_ml_engineer",
  "data_scientist",
  "data_analyst",
  "product_manager",
  "financial_analyst",
  "mechanical_engineer",
  "electrical_engineer",
];

/**
 * Onboarding's Role question (2026-11-16): the hand-picked roles above as
 * tiles, picked with one click as Figma's role page offers its roles, and a
 * search of the rest under them. The Role filter has 48 roles, too many to
 * show as tiles and too many to scroll through in a list, which was all the
 * page had. A tile's pick is not shown again as a pill under the search, so
 * no role shows twice. Settings keeps `RolePicker`, the search alone.
 *
 * "LOOKING FOR SOMETHING ELSE?" (2026-11-16) leads into the search, not "Or
 * search all 48 roles": a count says nothing a student needs, and the search
 * also takes a role WorkIt doesn't list. Typed there, it becomes one of the
 * student's own roles (`customRoles`), found in job titles; the line says
 * so, since a search box alone reads as a list to pick from.
 */
export function PopularRoleChoices({
  answers,
  set,
  roles,
  labelledBy,
}: PieceProps & { roles: PickOption[] }) {
  const popular = POPULAR_ROLES.flatMap((slug) => roles.filter((r) => r.value === slug));
  const isPopular = (value: string) => popular.some((r) => r.value === value);
  return (
    <>
      <Choices dense={false} columns="grid-cols-1 sm:grid-cols-2" labelledBy={labelledBy}>
        {popular.map((o) => (
          <Choice
            dense={false}
            key={o.value}
            pressed={answers.roles.includes(o.value)}
            onClick={() => set({ roles: toggle(answers.roles, o.value) })}
          >
            {o.label}
          </Choice>
        ))}
      </Choices>
      <MoreRoles answers={answers} set={set} roles={roles} isPopular={isPopular} />
    </>
  );
}

/** "Looking for something else?" (2026-11-17): every other role WorkIt
 *  lists, or one the student types, searched in a dialog (./search-dialog). */
function MoreRoles({
  answers,
  set,
  roles,
  isPopular,
}: Pick<PieceProps, "answers" | "set"> & {
  roles: PickOption[];
  isPopular: (value: string) => boolean;
}) {
  return (
    <SearchDialog
      className="short:lg:mt-4 mt-6"
      button="Search All Roles"
      title="Find Your Role"
      description="Search every role WorkIt lists, or type your own if you don't see it."
      label="More Roles"
      placeholder="Search or type a role"
      empty="No role by that name."
      options={roleOptions(
        roles.filter((r) => !isPopular(r.value)),
        answers.customRoles,
      )}
      values={roleValues({
        roles: answers.roles.filter((r) => !isPopular(r)),
        customRoles: answers.customRoles,
      })}
      onChange={(next) => {
        const picked = splitRoleValues(next);
        set({
          roles: [...answers.roles.filter(isPopular), ...picked.roles],
          customRoles: picked.customRoles,
        });
      }}
      create={addCustomRole(answers.customRoles, (customRoles) => set({ customRoles }))}
    />
  );
}

export function JobTypeChoices({ answers, set, dense = false, labelledBy }: PieceProps) {
  return (
    <Choices dense={dense} columns="grid-cols-2" labelledBy={labelledBy}>
      {JOB_TYPE_OPTIONS.map((o) => (
        <Choice
          dense={dense}
          key={o.value}
          pressed={answers.jobTypes.includes(o.value)}
          onClick={() => {
            const jobTypes = toggle(answers.jobTypes, o.value);
            const units = payUnits(jobTypes);
            // The salary's unit follows the job types (payUnits): when the
            // picks no longer offer the unit set, it moves to one they do,
            // and a range in the old unit goes, since it meant the other
            // unit's figures. It is set here, not forced on the picker, so
            // the /hr /yr toggle can still change it among the units
            // offered, and the unit saved is the one shown.
            set({
              jobTypes,
              ...(!units.includes(answers.payPer)
                ? { payPer: units[0], minPay: null, maxPay: null }
                : {}),
              ...(jobTypes.includes("internship") ? {} : { startTerms: [] }),
            });
          }}
        >
          {o.label}
        </Choice>
      ))}
    </Choices>
  );
}

export function StartDatePicker({
  answers,
  set,
  seasons,
  dense = false,
}: PieceProps & { seasons: PickOption[] }) {
  if (seasons.length === 0)
    return <p className="text-body text-ink-meta">No start dates in the feed yet.</p>;
  return (
    <SearchPicker
      size={dense ? "default" : "lg"}
      label="Start Dates"
      placeholder="Search a season, or leave empty for any"
      empty="No season by that name has jobs."
      options={seasons}
      values={answers.startTerms}
      onChange={(next) => set({ startTerms: next })}
    />
  );
}

/** Onboarding's Start Date: the seasons as tiles (2026-11-16). As a
 *  dropdown it opened over the page's foot and was cut off, and a list to
 *  open is one more step than tiles in view. The next `NEXT_SEASONS` show
 *  first, where nearly every posting is (on 2026-11-16, 12,484 of 12,581
 *  postings naming an upcoming season ran through Spring 2028); Show Later
 *  Dates adds the rest. */
const NEXT_SEASONS = 6;

export function StartDateChoices({
  answers,
  set,
  seasons,
  labelledBy,
}: PieceProps & { seasons: PickOption[] }) {
  const [later, setLater] = useState(false);
  if (seasons.length === 0)
    return <p className="text-body text-ink-meta">No start dates in the feed yet.</p>;
  // A later season already picked keeps the rest in view.
  const showAll =
    later || seasons.slice(NEXT_SEASONS).some((o) => answers.startTerms.includes(o.value));
  return (
    <>
      <Choices dense={false} columns="grid-cols-2" labelledBy={labelledBy}>
        {(showAll ? seasons : seasons.slice(0, NEXT_SEASONS)).map((o) => (
          <Choice
            dense={false}
            key={o.value}
            pressed={answers.startTerms.includes(o.value)}
            onClick={() => set({ startTerms: toggle(answers.startTerms, o.value) })}
          >
            {o.label}
          </Choice>
        ))}
      </Choices>
      {!showAll && seasons.length > NEXT_SEASONS && (
        <Button variant="section" className="mt-3" onClick={() => setLater(true)}>
          Show Later Dates
        </Button>
      )}
    </>
  );
}

/** "$25+ an hour", "$80k+ a year": a preset as a sentence says it. */
const payWords = (value: number, per: "hour" | "year") =>
  per === "hour" ? `$${value}+ an hour` : `$${Math.round(value / 1000)}k+ a year`;

/**
 * Onboarding's Pay page (2026-11-16): one question, the pay the student aims for,
 * as tiles. Any Pay first, which shows the many jobs that state no pay; then
 * the Jobs page's presets for the unit the job types are paid in, with a
 * segmented Hourly / Yearly only when the job types mix the two; then a
 * field for a minimum of the student's own. The filter's SalaryPicker drew
 * two rows of pills and a min-to-max pair whose example placeholders read as
 * filled values, which the user found ugly; a maximum is no question a
 * student asks of a first job, so onboarding asks only the minimum and All
 * Filters keeps the range.
 */
export function PayChoices({ answers, set, labelledBy }: PieceProps) {
  // BOTH UNITS IN VIEW, THE ONES THE JOB TYPES AREN'T PAID IN GREYED
  // (2026-11-17): payUnits says how the picks are paid (internships and
  // part-time by the hour, full-time by the year, contracts and mixes
  // either). The unit is `payPer`, which Job Type keeps among those, so the
  // page starts there and the switch changes it. A unit outside them falls
  // back to the first offered, for a page opened by its address before Job
  // Type. Hidden, the switch left a full-time student no hourly rate to see;
  // read from the job types until a goal was set, it held an intern on
  // Hourly with no way to tell why.
  const units = payUnits(answers.jobTypes);
  const per = units.includes(answers.payPer) ? answers.payPer : units[0];
  const presets = PAY_OPTIONS[per];
  const preset = presets.some((o) => o.value === answers.minPay) && answers.maxPay == null;
  // The field keeps what the student typed: drawn from minPay, a typed
  // 80000 matched the $80k preset and the field emptied mid-typing. A tile's
  // press or the unit's change clears it.
  const [own, setOwn] = useState(
    answers.minPay != null && !preset ? formatPay(String(answers.minPay), per) : "",
  );
  return (
    <>
      <SegmentedToggle
        label="Pay by"
        size="lg"
        // A glyph beside each word (the kit's `icon` draws the glyph alone):
        // a clock for an hourly rate, a calendar for a yearly salary.
        options={[
          {
            value: "hour",
            label: (
              <>
                <ClockIcon className="size-4" />
                Hourly
              </>
            ),
            ariaLabel: "Hourly",
            disabled: !units.includes("hour"),
          },
          {
            value: "year",
            label: (
              <>
                <CalendarIcon className="size-4" />
                Yearly
              </>
            ),
            ariaLabel: "Yearly",
            disabled: !units.includes("year"),
          },
        ]}
        value={per}
        // A minimum means nothing in the other unit, so it goes.
        onValueChange={(next) => {
          setOwn("");
          set({ payPer: next as "hour" | "year", minPay: null, maxPay: null });
        }}
      />
      {/* Why the other unit is greyed: a disabled option shows no tooltip.
          Only then: with both open, the switch says enough, and the line
          cost the page its fit on a short window (2026-11-17). */}
      {units.length > 1 ? (
        <div className="short:lg:mb-4 mb-5" />
      ) : (
        <p className="text-body text-ink-meta short:lg:mb-3 mt-2 mb-5">
          {units[0] === "hour"
            ? "Internships and part-time jobs pay by the hour."
            : "Full-time jobs pay a yearly salary."}
        </p>
      )}
      <Choices dense={false} columns="grid-cols-1 sm:grid-cols-2" labelledBy={labelledBy}>
        <ChoiceTile
          kind="radio"
          pressed={answers.minPay == null && answers.maxPay == null}
          onClick={() => {
            setOwn("");
            set({ minPay: null, maxPay: null, payPer: per });
          }}
        >
          Any pay
        </ChoiceTile>
        {presets.map((o) => (
          <ChoiceTile
            key={o.value}
            kind="radio"
            pressed={answers.minPay === o.value && answers.maxPay == null}
            onClick={() => {
              setOwn("");
              set({ minPay: o.value, maxPay: null, payPer: per });
            }}
          >
            {payWords(o.value, per)}
          </ChoiceTile>
        ))}
      </Choices>
      <div className="short:lg:mt-3 mt-5 max-w-xs">
        <TextField
          id="onboarding-own-pay"
          label={
            per === "hour" ? "Or set your own goal, per hour" : "Or set your own goal, per year"
          }
          size="lg"
          // Shown as money while it is typed: "$90,000", "$22.50" (./pay-format).
          inputMode={per === "hour" ? "decimal" : "numeric"}
          placeholder={per === "hour" ? "$40" : "$90,000"}
          value={own}
          onChange={(event) => {
            const shown = formatPay(event.target.value, per);
            setOwn(shown);
            set({ minPay: payAmount(shown), maxPay: null, payPer: per });
          }}
        />
      </div>
    </>
  );
}

export function LevelChoices({ answers, set, dense = false, labelledBy }: PieceProps) {
  return (
    <Choices dense={dense} columns="grid-cols-1 sm:grid-cols-2" labelledBy={labelledBy}>
      {EXPERIENCE_OPTIONS.map((o) => (
        <Choice
          dense={dense}
          key={o.value}
          pressed={answers.levels.includes(o.value)}
          onClick={() => set({ levels: toggle(answers.levels, o.value) })}
        >
          {o.label}
        </Choice>
      ))}
    </Choices>
  );
}

export function WorkplaceChoices({ answers, set, dense = false, labelledBy }: PieceProps) {
  return (
    <Choices dense={dense} columns="grid-cols-1 sm:grid-cols-3" labelledBy={labelledBy}>
      {WORKPLACE_OPTIONS.map((o) => (
        <Choice
          dense={dense}
          key={o.value}
          Icon={workStyleIcon(o.value)}
          pressed={answers.workStyles.includes(o.value)}
          onClick={() => set({ workStyles: toggle(answers.workStyles, o.value) })}
        >
          {o.label}
        </Choice>
      ))}
    </Choices>
  );
}

export function PlacesPicker({
  answers,
  set,
  places,
  dense = false,
}: PieceProps & { places: PickOption[] }) {
  return (
    <SearchPicker
      size={dense ? "default" : "lg"}
      label="Places"
      placeholder="Search a state or country, or leave empty for anywhere"
      empty="No place by that name has jobs."
      options={places}
      values={answers.places}
      onChange={(next) => set({ places: next })}
    />
  );
}

/** Onboarding's Location tiles (2026-11-17), by code (GET /jobs/locations):
 *  the states with the most postings on that day (California 4,551, Texas
 *  2,892, New York 2,189, Illinois 1,779, Florida 1,547, Virginia 1,498,
 *  Massachusetts 1,484), with Washington (1,056) for its tech employers.
 *  Revisit by what students pick, as POPULAR_ROLES. */
const POPULAR_PLACES = [
  "US-CA",
  "US-NY",
  "US-TX",
  "US-WA",
  "US-MA",
  "US-IL",
  "US-FL",
  "US-VA",
] as const;

/**
 * Onboarding's Location page (2026-11-17), laid out as Role's: the states
 * students most often want as tiles, and every other place, the United
 * States and other countries among them, searched in a dialog
 * (./search-dialog). It was a button under Where's workplace tiles, which
 * read as an extra; as a dropdown there it made the page scroll. Settings
 * keeps `PlacesPicker`.
 */
export function PlaceChoices({
  answers,
  set,
  places,
  labelledBy,
}: PieceProps & { places: PickOption[] }) {
  const popular = POPULAR_PLACES.flatMap((code) => places.filter((p) => p.value === code));
  const isPopular = (value: string) => popular.some((p) => p.value === value);
  return (
    <>
      <Choices dense={false} columns="grid-cols-1 sm:grid-cols-2" labelledBy={labelledBy}>
        {popular.map((o) => (
          <Choice
            dense={false}
            key={o.value}
            pressed={answers.places.includes(o.value)}
            onClick={() => set({ places: toggle(answers.places, o.value) })}
          >
            {o.label}
          </Choice>
        ))}
      </Choices>
      <SearchDialog
        className="short:lg:mt-4 mt-6"
        button="Search All Locations"
        title="Choose Locations"
        description="Search every state and country WorkIt has jobs in."
        label="Places"
        placeholder="Search a state or country"
        empty="No place by that name has jobs."
        options={places.filter((p) => !isPopular(p.value))}
        values={answers.places.filter((p) => !isPopular(p))}
        onChange={(next) => set({ places: [...answers.places.filter(isPopular), ...next] })}
      />
    </>
  );
}

/** Pay is part of the role (KAN-283): its units follow the job types picked. */
export function SalaryControl({ answers, set, dense = false }: PieceProps) {
  return (
    <SalaryPicker
      size={dense ? "default" : "lg"}
      units={payUnits(answers.jobTypes)}
      presets={PAY_OPTIONS}
      minPay={answers.minPay}
      maxPay={answers.maxPay}
      payPer={answers.payPer}
      onChange={(minPay, maxPay, per) => set({ minPay, maxPay, payPer: per })}
    />
  );
}

/** Settings' Job Preferences: every question at once, each in its Field. */
export function RoleStep({
  answers,
  set,
  roles,
  places,
  seasons,
  dense = false,
}: StepProps & {
  roles: PickOption[];
  places: PickOption[];
  seasons: PickOption[];
  /** Settings' Job Preferences: the app's own sizes (above), h3 headings. */
  dense?: boolean;
}) {
  const piece = { answers, set, dense };
  return (
    <>
      <Field dense={dense} Icon={RoleIcon} label="Role" required>
        <RolePicker {...piece} roles={roles} />
      </Field>
      <Field dense={dense} Icon={JobTypeIcon} label="Job Type" required>
        <JobTypeChoices {...piece} />
      </Field>
      {answers.jobTypes.includes("internship") && (
        <Field dense={dense} Icon={CalendarIcon} label="Start Date" tag={false}>
          <StartDatePicker {...piece} seasons={seasons} />
        </Field>
      )}
      {/* After Job Type, which says what kind of job: this says how much
          experience it asks for, and internships count as Entry Level, so
          no pair of the two empties the feed (KAN-284). */}
      <Field dense={dense} Icon={LevelIcon} label="Experience Level" tag={false}>
        <LevelChoices {...piece} />
      </Field>
      <Field dense={dense} Icon={workStyleIcon("onsite")} label="Workplace" required>
        <WorkplaceChoices {...piece} />
      </Field>
      <Field dense={dense} Icon={PinIcon} label="Location" tag={false}>
        <PlacesPicker {...piece} places={places} />
      </Field>
      <Field dense={dense} Icon={CoinIcon} label="Salary" tag={false}>
        <SalaryControl {...piece} />
      </Field>
    </>
  );
}

/** A question's answers: onboarding's tiles in a grid (`columns`), or in
 *  Settings (`dense`) a wrapping row of chips. */
function Choices({
  dense,
  columns,
  labelledBy,
  children,
}: {
  dense: boolean;
  columns: string;
  labelledBy?: string;
  children: ReactNode;
}) {
  return (
    <div
      role={labelledBy ? "group" : undefined}
      aria-labelledby={labelledBy}
      className={dense ? "flex flex-wrap gap-2" : cn("short:lg:gap-2 grid gap-2 lg:gap-3", columns)}
    >
      {children}
    </div>
  );
}

/** One answer: onboarding's ChoiceTile, or in Settings (`dense`) the
 *  Jobs page's filter chip, which shares its pressed look. */
function Choice({
  dense,
  pressed,
  onClick,
  Icon,
  children,
}: {
  dense: boolean;
  pressed: boolean;
  onClick: () => void;
  Icon?: Glyph;
  children: ReactNode;
}) {
  if (!dense) {
    return (
      <ChoiceTile pressed={pressed} onClick={onClick} Icon={Icon}>
        {children}
      </ChoiceTile>
    );
  }
  return (
    <Chip pressed={pressed} onClick={onClick}>
      {Icon && <Icon aria-hidden />}
      {children}
    </Chip>
  );
}

/** One question on the right: its glyph and label, a red star when it must be
 *  answered to go on, "Optional" when it need not be.
 *
 *  THE SCREEN HAS THREE TYPE SIZES, AT EVERY WIDTH: 20px for these labels,
 *  16px for every answer (tiles, chips, pills, typed text) and 14px for every
 *  note beside one. The answers' size is text-subtitle, whose own weight is
 *  600, so each answer sets its weight. */
/** A Field's heading id, from its label; its hint is the same id plus
 *  "-hint". */
export const fieldId = (label: string) => `field-${label.toLowerCase().replaceAll(" ", "-")}`;

export function Field({
  Icon,
  label,
  hint,
  required = false,
  tag = true,
  dense = false,
  children,
}: {
  Icon: Glyph;
  label: string;
  /** A 14px note under the label: the question as forms word it. */
  hint?: string;
  required?: boolean;
  /** Whether the heading says "Optional" (or * when required). A heading over
   *  a result, not a question, says neither: on the resume preview "Optional"
   *  read as if the reading were optional (KAN-732). Nor does an optional
   *  question beside required ones, which carry the * (RoleStep, KAN-829). */
  tag?: boolean;
  /** Settings' size (RoleStep's `dense`): a 14px heading, 16px apart. */
  dense?: boolean;
  children: ReactNode;
}) {
  const id = fieldId(label);
  const Heading = dense ? "h3" : "h2";
  return (
    <section
      aria-labelledby={id}
      className={cn(
        "border-border-subtle border-t first:border-t-0 first:pt-0",
        dense ? "py-4" : "py-8",
      )}
    >
      <Heading
        id={id}
        className={cn(
          "text-ink flex items-center font-semibold",
          dense ? "text-body mb-2.5 gap-2" : "text-title mb-4 gap-2.5",
        )}
      >
        <Icon className={cn("text-ink-meta shrink-0", dense ? "size-4" : "size-5")} />
        {label}
        {!tag ? null : required ? (
          <span className="text-danger" aria-label="required">
            *
          </span>
        ) : (
          <span
            className={cn("text-ink-meta ml-auto font-normal", dense ? "text-note" : "text-body")}
          >
            Optional
          </span>
        )}
      </Heading>
      {hint && (
        <p id={`${id}-hint`} className="text-body text-ink-meta -mt-2 mb-4">
          {hint}
        </p>
      )}
      {children}
    </section>
  );
}
