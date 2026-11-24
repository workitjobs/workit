"use client";

import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, useTransition } from "react";

import { CompanyLogo } from "@/components/company-logo";
import { LightningRoundedIcon } from "@/components/custom-icons";
import { ChevronDownIcon } from "@/components/icons";
import { MatchBadge } from "@/components/match-badge";
import { Checkbox } from "@/components/shadcn/checkbox";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/section-heading";
import { SectionLink } from "@/components/ui/section-link";
import { Tip } from "@/components/ui/tip";
import { useToast } from "@/components/ui/toast";
import { openNextApplication } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

import { hasApplied } from "../applied";
import { queueJob, type ApplicationStage } from "../auto-apply/actions";
import { openedNote } from "../auto-apply/opened-note";
import { ApplyButton } from "../jobs/apply-button";
import { ApplySplitButton } from "../jobs/apply-split-button";
import { stagesNow } from "../jobs/feed-stages";
import { SaveJobButton } from "../jobs/save-job-button";
import { readStageChanges, rememberStage, subscribeStageChanges } from "../jobs/shown-list";
import { TopMatchLink } from "./top-match-link";
import { LIST, SHOWN } from "./top-matches-frame";
import type { LogoSrc } from "@/lib/job-logo";

/** One Top Matches row, as ./top-matches.tsx reads it: plain data, so it can
 *  cross into this client component. `posted` is already words. */
export type TopMatchRow = {
  id: string;
  title: string;
  company: string;
  logoUrl: LogoSrc;
  applyUrl: string;
  match: number | null;
  posted: string | null;
  /** Its hiring system is one auto apply can fill (Greenhouse for now). */
  autoApply: boolean;
  stage: ApplicationStage | null;
};

/** Why a row can't be picked for the queue, in the words its row shows; null
 *  when it can. A saved job counts as no application, as the job's own Auto
 *  Apply button treats it. */
function blockedReason(row: TopMatchRow): string | null {
  if (row.stage === "queued") return "Already queued";
  if (hasApplied(row.stage)) return "Applied";
  if (row.stage === "needs_you") return "Needs you";
  if (row.stage === "skipped") return "Skipped";
  if (!row.autoApply) return "Auto Apply can't fill this one";
  return null;
}

/** Why the heading's Auto Apply is off, in its tooltip. */
const NO_PICKS = "None of your matches can be auto applied to right now.";

/**
 * Top Matches' heading and rows (KAN-342), and AUTO APPLY'S PICKING MODE.
 *
 * A row is a well with the logo, the title (its link to the job posting
 * page, which makes that page's Back return here: ./top-match-link.tsx), the
 * company, the match ring and when it was posted, then THE JOB CARD'S OWN
 * SAVE AND APPLY (KAN-828): Save as the card's bare bookmark, and Apply as
 * the card's, the Auto Apply split button on a job auto apply can fill
 * (../jobs/apply-split-button.tsx) and Apply Now on any other. The rows had
 * a bordered Save square and a bordered Apply Now on every job, so Home
 * offered less than the card for the same job. Tailor My Resume sat between
 * them and was taken out at the user's ask: the list is for choosing what
 * to apply to, and Tailor is one click away on the job's page.
 *
 * THE LIST SHOWS `SHOWN` ROWS AND SEE MORE (KAN-828): it scrolled inside
 * its tile, so the mouse wheel over it moved the list and not the page.
 * See More shows the rest in place, and See Less folds them back.
 *
 * Each row's stage is the server's, with the seeker's changes since
 * `drawnAt` laid over it (../jobs/feed-stages, as the Jobs page does): a
 * job queued from its row's Apply, or saved, keeps that stage when picking
 * mode below draws the row again, and picking mode never offers it.
 *
 * Auto Apply, at the heading's right beside See More Matches, turns the list
 * into a picker of the seeker's best matches that auto apply can fill
 * (`autoRows`, the same scores with ?auto_apply=true): the top list itself
 * may hold none of them, since auto apply fills Greenhouse alone for now,
 * and a picker of rows that can't be picked helped nobody. Each row gets a
 * checkbox in front, the whole row toggles it, and its buttons step aside,
 * so a click picks rather than saves or applies. A row that already has a
 * stage (queued, applied) is dimmed with it. "Add N to Queue"
 * queues every pick through the same call as a job's own Auto Apply button
 * (queueJob), then, as that button does, asks the extension to open the
 * oldest queued job in its background tab (openNextApplication). A toast
 * says how many went in, with View Queue to the Auto Apply page. The
 * seeker picks each job themself, so this keeps the rule that auto apply
 * never queues a saved job on its own (frontend/CLAUDE.md). It is off, with
 * a tooltip that says why, when no match can be picked.
 */
export function TopMatchesList({
  rows,
  autoRows,
  canMarkApplied,
  drawnAt,
}: {
  rows: TopMatchRow[];
  /** The best matches auto apply can fill, for picking mode. */
  autoRows: TopMatchRow[];
  canMarkApplied: boolean;
  /** When the server read the stages (ms since the epoch). */
  drawnAt: number;
}) {
  const router = useRouter();
  const toast = useToast();
  const [picking, setPicking] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [all, setAll] = useState(false);
  const [pending, start] = useTransition();
  // Each job's stage as of now: the server's, with the seeker's changes since.
  const changes = useSyncExternalStore(subscribeStageChanges, readStageChanges, () => null);
  const stages = stagesNow(
    Object.fromEntries([...rows, ...autoRows].map((row) => [row.id, row.stage])),
    changes,
    drawnAt,
  );

  const withStage = (picking ? autoRows : rows).map((row) => ({
    ...row,
    stage: stages[row.id] ?? null,
  }));
  const shown = all ? withStage : withStage.slice(0, SHOWN);
  const pickable = autoRows.filter(
    (row) => blockedReason({ ...row, stage: stages[row.id] ?? null }) === null,
  );
  const noPicks = pickable.length === 0;

  function leave() {
    setPicking(false);
    setPicked(new Set());
  }

  function toggle(id: string) {
    setPicked((now) => {
      const next = new Set(now);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function addToQueue() {
    const ids = [...picked];
    start(async () => {
      // One at a time, in the list's order, so the queue keeps the best first.
      let queued = 0;
      let failed = 0;
      for (const id of ids) {
        const result = await queueJob(id);
        if (result.stage) {
          // Every other button for the job follows (KAN-217).
          rememberStage(id, result.stage);
          if (result.stage === "queued") queued++;
        } else failed++;
      }
      leave();
      if (queued > 0) {
        void openNextApplication().then((result) => {
          if (!result.opened && (result.reason === "signed_out" || result.reason === "error")) {
            toast.show({ message: openedNote(result) });
          }
        });
      }
      toast.show({
        message:
          queued === 0
            ? "None of those jobs could be queued. Try again in a moment."
            : `${queued} ${queued === 1 ? "job is" : "jobs are"} queued for Auto Apply.${
                failed > 0 ? ` ${failed} couldn't be queued.` : ""
              }`,
        action:
          queued > 0
            ? { label: "View Queue", onClick: () => router.push("/auto-apply") }
            : undefined,
      });
    });
  }

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeading id="top-matches">Top Matches</SectionHeading>
          <p className="text-body text-ink-meta mt-1">
            {picking
              ? "Your best matches that Auto Apply can fill. Pick the ones to queue."
              : "Your highest-scoring jobs right now."}
          </p>
        </div>
        {picking ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm" onClick={leave} disabled={pending}>
              Cancel
            </Button>
            <Button size="sm" onClick={addToQueue} disabled={picked.size === 0 || pending}>
              <LightningRoundedIcon aria-hidden className="size-4" />
              {pending
                ? "Adding…"
                : picked.size === 0
                  ? "Add to Queue"
                  : `Add ${picked.size} to Queue`}
            </Button>
          </div>
        ) : (
          // See More Matches is a text link, as every Home card's way onward
          // is (SectionLink, KAN-821): a bordered button beside Auto Apply
          // drew two actions of one weight.
          <div className="flex flex-wrap items-center gap-4">
            {/* Off when no match can be picked, and says why in a tooltip
                (KAN-828; a `title` reached neither touch nor a keyboard). It
                stays focusable and hoverable, aria-disabled rather than
                disabled, so the tooltip can show, as Scout's Send does. */}
            <Tip label={NO_PICKS} disabled={!noPicks}>
              <Button
                variant="secondary"
                size="sm"
                aria-disabled={noPicks || undefined}
                onClick={() => {
                  if (!noPicks) setPicking(true);
                }}
                className="aria-disabled:hover:bg-panel aria-disabled:cursor-default aria-disabled:opacity-50 aria-disabled:active:scale-100"
              >
                <LightningRoundedIcon aria-hidden className="size-4" />
                Auto Apply
              </Button>
            </Tip>
            <SectionLink href="/jobs?sort=match">See More Matches</SectionLink>
          </div>
        )}
      </div>

      <ul id="top-matches-rows" aria-label="Top Matches" className={LIST}>
        {shown.map((row, i) => {
          const blocked = blockedReason(row);
          const isPicked = picked.has(row.id);
          const match = row.match != null && <MatchBadge score={row.match} />;
          const details = (
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <CompanyLogo
                name={row.company}
                src={row.logoUrl}
                className="text-note rounded-control size-10 shrink-0"
              />
              <div className="min-w-0 flex-1">
                {picking ? (
                  <p className="text-label text-ink @max-4xl/main:line-clamp-2 @4xl/main:truncate">
                    {row.title}
                  </p>
                ) : (
                  <TopMatchLink
                    href={`/jobs/${encodeURIComponent(row.id)}`}
                    className="text-label text-ink hover:text-brand focus-visible:ring-brand-ring block rounded-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none @max-4xl/main:line-clamp-2 @4xl/main:truncate"
                  >
                    {row.title}
                  </TopMatchLink>
                )}
                {/* The company, then when it was posted, as the job
                    cards' meta line reads ("HP · 21 days ago"): the
                    company truncates first, so the age always shows. */}
                <div className="text-note text-ink-meta mt-1 flex min-w-0 items-center gap-x-1.5">
                  <span className="min-w-0 truncate">{row.company}</span>
                  {row.posted && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span className="shrink-0">{row.posted}</span>
                    </>
                  )}
                  {/* Picking has no buttons' row, so the match stays
                      here below @4xl/main; otherwise it leads that row. */}
                  {picking && match && (
                    <span className="ml-1 flex shrink-0 @4xl/main:hidden">{match}</span>
                  )}
                </div>
              </div>
              {/* From @4xl/main the match is a column of its own
                  (KAN-423), against Save and Apply, so the scores
                  line up down the list. The posted date was a second
                  pill column until 2026-11-10: two pills in fixed
                  columns floated in the middle of the row, apart from
                  both the title and the buttons. */}
              {match && <span className="hidden shrink-0 pl-4 @4xl/main:flex">{match}</span>}
            </div>
          );

          return (
            // The rows rise in as the scores arrive, 30ms apart and capped
            // at the eighth, so the list never makes anyone wait.
            <li
              key={row.id}
              style={{ animationDelay: `${Math.min(i, 8) * 30}ms` }}
              className="animate-rise flex shrink-0"
            >
              {picking ? (
                // The whole row is the checkbox's label, so a click anywhere
                // on it picks; a blocked row says why instead.
                <label
                  className={cn(
                    "bg-well rounded-card flex w-full items-center gap-3 p-3 transition-colors duration-150",
                    blocked
                      ? "cursor-not-allowed opacity-60"
                      : "hover:bg-brand-tint has-[[data-checked]]:bg-brand-tint cursor-pointer",
                  )}
                >
                  {/* border-ink-meta, as CheckRowBox's: the vendored
                      input hairline drew the empty box at 1.19:1. */}
                  <Checkbox
                    className="border-ink-meta"
                    checked={blocked ? row.stage === "queued" : isPicked}
                    disabled={blocked !== null || pending}
                    onCheckedChange={() => toggle(row.id)}
                    aria-label={`Queue ${row.title} at ${row.company}`}
                  />
                  {details}
                  {blocked && (
                    <span className="text-note text-ink-meta shrink-0 @max-xl/main:hidden">
                      {blocked}
                    </span>
                  )}
                </label>
              ) : (
                <div className="bg-well rounded-card flex w-full flex-col gap-3 p-3 @xl/main:flex-row @xl/main:items-center">
                  {details}
                  {/* Save, then Apply, as the job card draws them: their
                      own full-width line below @xl/main, since beside the
                      text on a phone they squeezed the title to two words a
                      line, with Apply growing to fill it. Below @4xl/main
                      the match leads the line: on the company's line it cut
                      the name to "Hewlett P…". */}
                  <div className="flex shrink-0 items-center gap-3 @max-xl/main:w-full">
                    {match && (
                      <span className="mr-auto flex shrink-0 @4xl/main:hidden">{match}</span>
                    )}
                    <SaveJobButton jobId={row.id} title={row.title} stage={row.stage} quiet />
                    {/* One slot wide enough for the split button, which
                        Apply Now fills too, so Save and the match sit at
                        one place down the list whichever Apply a row has. */}
                    <div className="flex @max-xl/main:flex-1 @xl/main:min-w-38">
                      {row.autoApply ? (
                        <ApplySplitButton
                          jobId={row.id}
                          title={row.title}
                          company={row.company}
                          applyUrl={row.applyUrl}
                          stage={row.stage}
                          canMarkApplied={canMarkApplied}
                          applied={hasApplied(row.stage)}
                          className="flex-1 *:first:grow"
                        />
                      ) : (
                        <ApplyButton
                          jobId={row.id}
                          title={row.title}
                          applyUrl={row.applyUrl}
                          canMarkApplied={canMarkApplied}
                          applied={hasApplied(row.stage)}
                          className="flex-1"
                        />
                      )}
                    </div>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {/* The rest of the list in place, under a rule across the card's
          foot, as Experiences' Show All sits under its rows. */}
      {withStage.length > SHOWN && (
        <div className="border-border-subtle -mx-5 mt-4 -mb-5 flex justify-center border-t py-2">
          <Button
            variant="section"
            aria-expanded={all}
            aria-controls="top-matches-rows"
            onClick={() => setAll((open) => !open)}
          >
            {all ? "See Less" : "See More"}
            <ChevronDownIcon className={cn("size-3.5", all && "rotate-180")} />
          </Button>
        </div>
      )}
    </>
  );
}
