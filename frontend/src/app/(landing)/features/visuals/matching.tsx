import { CaretDownIcon, CheckIcon, SortDescendingIcon } from "@phosphor-icons/react/ssr";

import { MatchGlyph } from "@/components/match-badge";
import { cn } from "@/lib/cn";
import { matchTier } from "@/lib/match";

import { hiringSystems } from "../../data";
import { FaviconLogo } from "../../favicon-logo";
import { candidate, matchingFeature, type MatchFactor } from "../../feature-data";
import { Label, Score, Vignette } from "./parts";

/** The Job Matching page's deep dives. The jobs and the factors are the
 *  tour's Matching stop's (feature-data.ts), so the two read as one story. */

const { profile, jobs, factorLabels } = matchingFeature;
const ranked = [...jobs].sort((a, b) => b.score - a.score);
const best = ranked[0];

/** Why the best job scored as it did: the student's bank beside the four
 *  things the score weighs (backend matching/scoring.py). */
export function ScoreVisual() {
  const factors = Object.keys(factorLabels) as MatchFactor[];
  return (
    <Vignette className="gap-3 px-4">
      <div className="surface-card flex items-center gap-3 rounded-2xl p-3">
        <span className="bg-brand-tint text-brand-ink grid size-9 shrink-0 place-items-center rounded-full text-[12px] font-bold">
          AM
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-ink text-[13px] font-semibold">{candidate.name}&rsquo;s bank</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {profile.skills.slice(0, 4).map((skill) => (
              <span
                key={skill}
                className="bg-brand-tint text-brand-ink rounded-full px-2 py-0.5 text-[10px] font-medium"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="surface-card rounded-2xl p-4">
        <div className="flex items-center gap-3">
          <FaviconLogo domain={best.domain} className="size-9" />
          <div className="min-w-0 flex-1">
            <p className="text-ink truncate text-[13px] font-semibold">{best.title}</p>
            <p className="text-ink-meta text-[11px]">{best.company}</p>
          </div>
          <Score score={best.score} className="text-[13px]" />
        </div>
        <div className="mt-4 grid gap-2">
          {factors.map((factor) => (
            <div key={factor} className="flex items-center gap-3">
              <span className="text-ink-muted w-20 shrink-0 text-[11px]">
                {factorLabels[factor]}
              </span>
              <span className="bg-brand-tint h-2 flex-1 overflow-hidden rounded-full">
                <span
                  className="bg-brand block h-full rounded-full"
                  style={{ width: `${best.factors[factor] * 100}%` }}
                />
              </span>
            </div>
          ))}
        </div>
      </div>
    </Vignette>
  );
}

/**
 * Why a job fits, as a Jobs page card's match rail shows it
 * (`(seeker)/jobs/match-rail.tsx`): the ring, the band and up to three
 * reasons, a tick for what fits and a dot for what to weigh. The reasons
 * are labels the API writes (backend services/matching/highlights.py).
 */
const REASONS = [
  { text: "Uses 3 of your skills", met: true },
  { text: "Fits your major", met: true },
  { text: "Asks for 1+ years", met: false },
];

export function ReasonsVisual() {
  return (
    <Vignette className="px-6">
      <div className="surface-card rounded-2xl p-4">
        <div className="flex items-center gap-3">
          <FaviconLogo domain={best.domain} className="size-9" />
          <div className="min-w-0 flex-1">
            <p className="text-ink truncate text-[13px] font-semibold">{best.title}</p>
            <p className="text-ink-meta text-[11px]">{best.company}</p>
          </div>
        </div>
        <div className="bg-well mt-4 flex items-center gap-4 rounded-xl p-3">
          <div className="relative grid size-20 shrink-0 place-items-center">
            <MatchGlyph score={best.score} className="absolute inset-0 size-20" />
            <span className="text-ink text-[17px] font-semibold tabular-nums">{best.score}%</span>
          </div>
          <div className="min-w-0">
            <p className="text-ink text-[14px] font-semibold">{matchTier(best.score)}</p>
            <ul className="mt-2 grid gap-1.5">
              {REASONS.map((reason) => (
                <li key={reason.text} className="text-ink flex items-center gap-2 text-[12px]">
                  {reason.met ? (
                    <CheckIcon weight="bold" className="text-positive-ink size-3.5 shrink-0" />
                  ) : (
                    <span className="bg-ink-meta mx-1 size-1.5 shrink-0 rounded-full" />
                  )}
                  {reason.text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Vignette>
  );
}

/** The Jobs page sorted by Best Match, a score on every card. */
export function BestMatchVisual() {
  return (
    <Vignette className="gap-2 px-6">
      <div className="mb-1 flex items-center justify-between">
        <Label className="flex items-center gap-1.5">
          <SortDescendingIcon className="size-3.5" />
          {jobs.length} job postings
        </Label>
        <span className="text-ink inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-[11px] font-semibold shadow-[inset_0_0_0_1px_rgb(15_23_42/0.12)]">
          Best Match
          <CaretDownIcon className="size-3" />
        </span>
      </div>
      {ranked.slice(0, 4).map((job, i) => (
        <div
          key={job.id}
          className={cn(
            "flex items-center gap-3 rounded-xl bg-white px-3 py-2 shadow-[0_10px_24px_-16px_rgb(16_48_94/0.5)] ring-1",
            i === 0 ? "ring-brand/50 ring-2" : "ring-slate-900/5",
          )}
        >
          <FaviconLogo domain={job.domain} className="size-8" />
          <div className="min-w-0 flex-1">
            <p className="text-ink truncate text-[12px] font-semibold">{job.title}</p>
            <p className="text-ink-meta text-[10px]">{job.company}</p>
          </div>
          <Score score={job.score} />
        </div>
      ))}
    </Vignette>
  );
}

/** Real employers on scraper/boards.csv, each on the hiring system its
 *  company job board is on there. */
const SOURCES = [
  {
    company: "Stripe",
    domain: "stripe.com",
    title: "Software Engineer Intern",
    system: "Greenhouse",
  },
  {
    company: "Palantir",
    domain: "palantir.com",
    title: "Software Engineer Intern",
    system: "Lever",
  },
  { company: "Ramp", domain: "ramp.com", title: "New Grad Software Engineer", system: "Ashby" },
] as const;

/** Postings from company job boards, each with the hiring system it came
 *  from and the way to the company's own application. */
export function SourcesVisual() {
  const logo = (name: string) => hiringSystems.find((system) => system.name === name)?.logo;
  return (
    <Vignette className="gap-2.5 px-6">
      {SOURCES.map((job) => {
        const src = logo(job.system);
        return (
          <div key={job.company} className="surface-card flex items-center gap-3 rounded-2xl p-3">
            <FaviconLogo domain={job.domain} className="size-9" />
            <div className="min-w-0 flex-1">
              <p className="text-ink truncate text-[12px] font-semibold">{job.title}</p>
              <p className="text-ink-meta flex items-center gap-1.5 text-[10px]">
                {job.company} · from
                {src && <FaviconLogo src={src} className="size-4 rounded-[4px] shadow-none" />}
                {job.system}
              </p>
            </div>
            <span className="text-brand-ink bg-brand-tint shrink-0 rounded-lg px-2.5 py-1 text-[11px] font-semibold">
              Apply Now
            </span>
          </div>
        );
      })}
    </Vignette>
  );
}
