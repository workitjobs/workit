"use client";

import type { ComponentType, ReactNode } from "react";

import {
  EXPERIENCE_OPTIONS,
  JOB_TYPE_OPTIONS,
  WORKPLACE_OPTIONS,
  type FeedFilters,
} from "@/app/(seeker)/jobs/filter-query";
import { FaviconLogo } from "@/app/(landing)/favicon-logo";
import type { PickOption } from "@/components/filter-controls";
import {
  CoinIcon,
  JobTypeIcon,
  LevelIcon,
  PinIcon,
  RoleIcon,
  UserIcon,
  workStyleIcon,
} from "@/components/icons";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";
import { matchColor } from "@/lib/match";

import { previewJobs } from "./preview-jobs";
import type { Page } from "./steps";

/**
 * Onboarding's right half, after Figma's sign-up (2026-11-16): a mock of the
 * student's own Jobs page that changes with every answer, as Figma's canvas
 * changes with each pick. Each answer lands as a filter chip, and the three
 * job cards under them follow the answers (./preview-jobs): a role brings
 * three well-known employers that hire for it (Data Scientist: Meta,
 * Spotify, Uber), the job type and level change the titles ("Software
 * Engineer Intern"), the workplace and place the line under them, and a
 * minimum pay drops a posting under it. A card that is new rises in. A
 * saved resume gives them match scores. So the screen the student lands on
 * after Find Jobs is the one they watched being built. It draws only the
 * feed's own questions (role through pay): the resume step has the resume
 * (./resume-panel) and the application questions an employer's form
 * (./application-panel), one graphic a stage. Cards pinned over its corner
 * on those pages drew two pictures at once until 2026-11-17.
 *
 * THIS PAGE'S QUESTION IS THE ONE DASHED, PULSING CHIP, beside the answered
 * ones, so the eye goes from the question on the left to where its answer
 * lands.
 *
 * The window's corner is a profile glyph, never the email's first letter:
 * an initial read as a stranger's avatar (2026-11-16).
 *
 * DECORATION, NOT CONTENT. The postings, their pay and the scores are made
 * up, so the whole panel is aria-hidden: the fields on the left are the
 * answers. From lg only; below it the question column is the whole screen,
 * as Figma's is on a phone.
 */

type Glyph = ComponentType<{ className?: string }>;

/** The cards' match scores once a resume is saved, best first. */
const SCORES = [94, 88, 81];

const labelOf = <V extends string>(options: { value: V; label: string }[], value: V) =>
  options.find((o) => o.value === value)?.label ?? value;

/** The first pick's label and "+N" for the rest, or null with none. */
function picked(values: string[], label: (value: string) => string): string | null {
  if (values.length === 0) return null;
  return values.length === 1 ? label(values[0]) : `${label(values[0])} +${values.length - 1}`;
}

/** "$35+/hr", "$120k–$150k/yr", or null with no pay set. */
export function payLabel({ minPay, maxPay, payPer }: FeedFilters): string | null {
  if (minPay == null && maxPay == null) return null;
  const money = (n: number) => (n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`);
  const per = payPer === "hour" ? "/hr" : "/yr";
  if (minPay != null && maxPay != null) return `${money(minPay)}–${money(maxPay)}${per}`;
  return minPay != null ? `${money(minPay)}+${per}` : `Up to ${money(maxPay!)}${per}`;
}

export function PreviewPanel({
  page,
  answers,
  roles,
  places,
  scored,
  unsure,
}: {
  page: Page;
  answers: FeedFilters;
  roles: PickOption[];
  places: PickOption[];
  /** A resume is saved: every job shows its match score. */
  scored: boolean;
  /** The pages left open with Not Sure Yet: their chips say "Any …". */
  unsure: ReadonlySet<Page>;
}) {
  const roleLabel = (v: string) => roles.find((o) => o.value === v)?.label ?? v;
  const placeLabel = (v: string) => places.find((o) => o.value === v)?.label ?? v;
  const jobTypeLabel = (v: string) => labelOf(JOB_TYPE_OPTIONS, v as never);
  const workplaceLabel = (v: string) => labelOf(WORKPLACE_OPTIONS, v as never);

  // `any` is the chip once the page is left open with Not Sure Yet
  // (2026-11-17): the Jobs page then shows every option there.
  type Chip = { page: Page; Icon: Glyph; empty: string; any: string; value: string | null };
  const chips = (
    [
      {
        page: "Role",
        Icon: RoleIcon,
        empty: "Role",
        any: "Any role",
        // The listed roles' names, then the student's own typed ones.
        value: picked([...answers.roles.map(roleLabel), ...answers.customRoles], (name) => name),
      },
      {
        page: "JobType",
        Icon: JobTypeIcon,
        empty: "Job Type",
        any: "Any job type",
        value: picked(answers.jobTypes, (v) => labelOf(JOB_TYPE_OPTIONS, v as never)),
      },
      {
        page: "Level",
        Icon: LevelIcon,
        empty: "Experience",
        any: "Any level",
        value: picked(answers.levels, (v) => labelOf(EXPERIENCE_OPTIONS, v as never)),
      },
      {
        page: "Where",
        Icon: workStyleIcon("onsite"),
        empty: "Workplace",
        any: "Any workplace",
        value: picked(answers.workStyles, (v) => labelOf(WORKPLACE_OPTIONS, v as never)),
      },
      {
        page: "Location",
        Icon: PinIcon,
        empty: "Location",
        any: "Anywhere",
        value: picked(answers.places, placeLabel),
      },
      { page: "Pay", Icon: CoinIcon, empty: "Salary", any: "Any pay", value: payLabel(answers) },
    ] satisfies Chip[]
  ).map((chip) => ({ ...chip, value: chip.value ?? (unsure.has(chip.page) ? chip.any : null) }));

  const jobs = previewJobs(
    answers,
    { role: roleLabel, place: placeLabel, jobType: jobTypeLabel, workplace: workplaceLabel },
    3,
    unsure.has("Role"),
  );

  return (
    <aside
      aria-hidden
      className="bg-brand-tint relative hidden items-center justify-center overflow-hidden px-10 py-12 lg:flex lg:w-1/2 xl:px-16"
    >
      <div className="bg-panel shadow-tile rounded-card relative w-full max-w-[38rem]">
        {/* The window's bar: the mark, the page's name and a profile glyph. */}
        <div className="border-border-subtle flex items-center justify-between border-b px-5 py-3.5">
          <Logo size="mark" decorative className="h-5" />
          <span className="text-body text-ink font-medium">Your Jobs</span>
          <span className="bg-well text-ink-muted flex size-7 items-center justify-center rounded-full">
            <UserIcon className="size-4" />
          </span>
        </div>

        <div className="flex flex-col gap-4 p-5">
          {/* ONLY THE ANSWERED CHIPS AND THIS PAGE'S, so the row grows as the
              student answers (2026-11-16). All six at once, five of them
              dashed and empty, wrapped to two rows on the first page and
              read as a form still to fill. This page's unanswered chip is
              the one dashed chip, and it pulses: no ring is needed to say
              which question it is. */}
          <div className="flex flex-wrap gap-2">
            {chips
              .filter((c) => c.value || c.page === page)
              .map((c) => (
                <span
                  key={c.empty}
                  className={cn(
                    "animate-pop text-note flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium transition-[background-color,border-color,color] duration-300",
                    c.value
                      ? "border-brand bg-brand-tint text-brand-ink"
                      : "border-brand/50 text-brand-ink border-dashed motion-safe:animate-pulse",
                  )}
                >
                  <c.Icon className="size-3.5 shrink-0" />
                  {c.value ?? c.empty}
                </span>
              ))}
          </div>

          {jobs.length === 0 ? (
            <EmptyJobs />
          ) : (
            <ul className="flex flex-col gap-3">
              {jobs.map((job, i) => (
                <li
                  key={job.key}
                  className="animate-rise border-border-subtle rounded-control flex items-center gap-3 border p-3.5"
                >
                  <FaviconLogo domain={job.domain} eager className="size-10" />
                  <div className="min-w-0 flex-1">
                    <p className="text-body text-ink truncate font-semibold">{job.title}</p>
                    <p className="text-note text-ink-meta mt-0.5 truncate">
                      {job.company} · {job.where}
                    </p>
                    <div className="mt-2 flex gap-1.5">
                      {job.jobType && <Tag>{job.jobType}</Tag>}
                      <Tag>{job.pay}</Tag>
                    </div>
                  </div>
                  {scored && <Score score={SCORES[i]} />}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  );
}

/** The list before a role is picked: one line that says what fills it. Three
 *  grey skeleton cards stood here and read as a page still loading, not one
 *  waiting for an answer (2026-11-16). Its height is the three cards', so
 *  the window does not jump when they arrive. */
function EmptyJobs() {
  return (
    <div className="border-border-control rounded-control text-ink-meta flex h-[22.5rem] flex-col items-center justify-center gap-3 border border-dashed text-center">
      <span className="bg-brand-tint text-brand flex size-10 items-center justify-center rounded-full">
        <RoleIcon className="size-5" />
      </span>
      <p className="text-body text-ink font-medium">Pick a role to see your jobs</p>
      <p className="text-note max-w-56">Each answer you give changes this list.</p>
    </div>
  );
}

function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="bg-well text-ink-muted text-note rounded-full px-2 py-0.5">{children}</span>
  );
}

const RING_R = 16;
const RING_C = 2 * Math.PI * RING_R;

/** A job's match, drawn only once a resume is saved: it pops in and its ring
 *  fills, the payoff of the upload. Before, every card showed a grey ring
 *  with a dash for five pages, which read as broken (2026-11-16). */
function Score({ score }: { score: number }) {
  return (
    <span className="animate-pop relative flex size-11 shrink-0 items-center justify-center">
      <svg viewBox="0 0 40 40" className="absolute inset-0 size-11 -rotate-90">
        <circle
          cx="20"
          cy="20"
          r={RING_R}
          fill="none"
          strokeWidth="3.5"
          className="stroke-border-subtle"
        />
        <circle
          cx="20"
          cy="20"
          r={RING_R}
          fill="none"
          strokeWidth="3.5"
          strokeLinecap="round"
          stroke={matchColor(score)}
          strokeDasharray={RING_C}
          strokeDashoffset={RING_C * (1 - score / 100)}
          className="animate-ring-fill"
        />
      </svg>
      <span className="text-note text-ink font-semibold">{score}</span>
    </span>
  );
}
