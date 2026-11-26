"use client";

import { CheckIcon } from "@phosphor-icons/react/ssr";

import { FaviconLogo } from "@/app/(landing)/favicon-logo";
import type { FeedFilters } from "@/app/(seeker)/jobs/filter-query";
import type { PickOption } from "@/components/filter-controls";
import { PROFILE_QUESTIONS, type AutofillAnswers } from "@/lib/autofill-answers";
import { cn } from "@/lib/cn";

import { LINKS, type Contact } from "./contact-fields";
import { previewJobs } from "./preview-jobs";
import type { Page } from "./steps";

/** The pages this graphic draws: the questions applications ask, not the
 *  feed's filters. */
export const APPLICATION_PAGES: readonly Page[] = [
  "Authorization",
  "Sponsorship",
  "Contact",
  "Links",
];

/** A fallback employer, when the student's answers give the panel no job. */
const ANY_JOB = { title: "Software Engineer Intern", company: "Stripe", domain: "stripe.com" };

type Row = { page: Page; label: string; value: string | null };

/**
 * Onboarding's right half on its last four pages (2026-11-17): one
 * employer's application, filling in with the student's answers as they
 * give them, the very fields WorkIt fills on every form (authorization,
 * sponsorship, where they live, their links). ONE GRAPHIC A STAGE: the Jobs
 * page mock answers the feed's questions (role through pay), the resume the
 * resume step's, and this the application's. These pages drew the Jobs page
 * mock with a small card pinned over it, two pictures at once, neither the
 * question's.
 *
 * The job is the student's own first preview posting (./preview-jobs), so
 * the form is for a job they asked for. The rows the page asks are the
 * ones that pulse until answered. Decoration, aria-hidden.
 */
export function ApplicationPanel({
  page,
  answers,
  roles,
  places,
  profile,
  contact,
  anyRole,
}: {
  page: Page;
  answers: FeedFilters;
  roles: PickOption[];
  places: PickOption[];
  profile: AutofillAnswers;
  contact: Contact;
  /** The student chose Not Sure Yet on Role. */
  anyRole: boolean;
}) {
  const label = (options: PickOption[]) => (v: string) =>
    options.find((o) => o.value === v)?.label ?? v;
  const job =
    previewJobs(
      answers,
      { role: label(roles), place: label(places), jobType: (v) => v, workplace: (v) => v },
      1,
      anyRole,
    )[0] ?? ANY_JOB;
  const answer = (key: "work_authorized_us" | "needs_sponsorship") => {
    const q = PROFILE_QUESTIONS.find((p) => p.key === key)!;
    return {
      label: q.question,
      value: q.options.find((o) => o.value === profile[key])?.label ?? null,
    };
  };
  const rows: Row[] = [
    { page: "Authorization", ...answer("work_authorized_us") },
    { page: "Sponsorship", ...answer("needs_sponsorship") },
    {
      page: "Contact",
      label: "Location (city and state)",
      value: contact.location?.trim() || null,
    },
    ...LINKS.map(({ key, label: name }) => ({
      page: "Links" as Page,
      label: name,
      value: contact[key]?.trim() || null,
    })),
  ];
  const filled = rows.filter((r) => r.value).length;

  return (
    <aside
      aria-hidden
      className="bg-brand-tint relative hidden items-center justify-center overflow-hidden px-10 py-12 lg:flex lg:w-1/2 xl:px-16"
    >
      <div className="flex w-full max-w-[34rem] flex-col items-center gap-5">
        <span className="bg-panel border-border-surface shadow-lift flex items-center gap-2.5 rounded-xl border py-2 pr-4 pl-2">
          <span className="bg-positive-tint text-positive-ink grid size-8 place-items-center rounded-lg">
            <CheckIcon weight="bold" className="size-4" />
          </span>
          <span>
            <span className="text-ink block text-sm font-semibold">
              WorkIt fills these in for you
            </span>
            <span className="text-ink-muted block text-xs">
              On every application: {filled} of {rows.length} ready
            </span>
          </span>
        </span>

        <div className="bg-panel shadow-tile rounded-card w-full">
          {/* The employer's form: its logo, the job, then its questions */}
          <div className="border-border-subtle flex items-center gap-3 border-b px-5 py-4">
            <FaviconLogo domain={job.domain} eager className="size-10" />
            <div className="min-w-0">
              <p className="text-body text-ink truncate font-semibold">Apply: {job.title}</p>
              <p className="text-note text-ink-meta truncate">{job.company}</p>
            </div>
          </div>
          <div className="flex flex-col gap-3.5 p-5">
            {rows.map((row) => {
              const asked = row.page === page;
              return (
                <div key={row.label} className="flex flex-col gap-1">
                  <span className="text-note text-ink-muted">{row.label}</span>
                  <span
                    className={cn(
                      "rounded-control text-body flex h-9 items-center justify-between gap-2 border px-3 transition-colors duration-300",
                      row.value
                        ? "border-positive/40 bg-positive-tint/40 text-ink"
                        : asked
                          ? "border-brand/50 text-brand-ink border-dashed motion-safe:animate-pulse"
                          : "border-border-subtle text-ink-subtle",
                    )}
                  >
                    <span className="truncate">{row.value ?? (asked ? "Your answer" : "")}</span>
                    {row.value && (
                      <CheckIcon
                        weight="bold"
                        className="text-positive-ink motion-safe:animate-pop size-3.5 shrink-0"
                      />
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
