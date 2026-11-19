import { CheckIcon, CursorIcon } from "@phosphor-icons/react/ssr";
import type { CSSProperties, ReactNode } from "react";

import { SparkleIcon } from "@/components/sparkle-icon";
import { cn } from "@/lib/cn";

import { Arrive } from "./arrive";
import { journey } from "./data";
import { followedJob, type FeatureId } from "./feature-data";
import { FaviconLogo } from "./favicon-logo";
import { FEATURES } from "./features/catalog";
import { FeatureIcon } from "./features/feature-icon";
import { CONTAINER, SectionHeading, StudioBox, studioGround, TYPE } from "./layout-parts";
import { tourTab } from "./tour-tabs";

/**
 * "One application, start to finish" (KAN-923), after Calendly's Book,
 * Prep, Capture, Follow up: four cards, one per step, joined by a rail, that
 * follow the one application the page follows (`followedJob`, Stripe). Each
 * card has its steps on a short timeline and a small picture in a framed
 * box that plays once as the box arrives (`Arrive`, `.journey-in` in
 * landing.css), then holds: no loop, so no pause control. It replaced the
 * applications route, which pinned a screen to a board. A server component;
 * only `Arrive` hydrates. Copy: `journey` in data.ts.
 */
export function Journey() {
  return (
    <section id="how-it-works" className="py-20 sm:py-28">
      <div className={CONTAINER}>
        <SectionHeading
          eyebrow={journey.eyebrow}
          title={journey.title}
          subtitle={journey.subtitle}
        />
        <ol className="mx-auto mt-14 max-w-5xl sm:mt-16">
          {journey.steps.map((step, i) => {
            const tab = tourTab(step.id);
            const page = FEATURES[tab.page];
            return (
              <li key={step.id} className="relative">
                {/* The rail between two cards: the step's colour fading
                    into the next one's. */}
                {i > 0 && (
                  <span
                    aria-hidden="true"
                    className="mx-auto block h-8 w-1 rounded-full sm:ml-[3.25rem]"
                    style={{
                      background: `linear-gradient(${FEATURES[tourTab(journey.steps[i - 1].id).page].glow}, ${page.glow})`,
                      opacity: 0.35,
                    }}
                  />
                )}
                <div className="surface-card grid gap-3 rounded-[2rem] p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-6">
                  <div className="px-4 pt-4 pb-2 sm:px-6 sm:pt-6 md:pb-6">
                    <p className={cn(TYPE.eyebrow, "text-ink-meta flex items-center gap-2")}>
                      <FeatureIcon
                        feature={{ icon: tab.icon, glow: page.glow, onGlow: page.onGlow }}
                      />
                      Step {i + 1}
                    </p>
                    <h3 className={cn(TYPE.card, "text-ink mt-4")}>{step.title}</h3>
                    <p className="text-ink-meta mt-2 text-pretty">{step.body}</p>
                    <ul className="mt-5 space-y-2.5">
                      {step.points.map((point) => (
                        <li
                          key={point}
                          className="text-ink-muted flex items-start gap-2.5 text-[15px]"
                        >
                          <span
                            aria-hidden="true"
                            className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full"
                            style={{ background: page.tint, color: page.onGlow.fill }}
                          >
                            <CheckIcon weight="bold" className="size-3" />
                          </span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {/* The picture plays as it comes up, not its card: on a
                      phone the card is a screen tall and the picture its
                      foot. */}
                  <Arrive className="flex">
                    <StudioBox
                      ground={studioGround({ tint: page.tint, glow: page.glow })}
                      className="flex min-h-[15rem] w-full items-center justify-center p-5"
                    >
                      <div aria-hidden="true" className="w-full max-w-[18.5rem]">
                        {PICTURES[step.id]}
                      </div>
                    </StudioBox>
                  </Arrive>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

/** One part of a picture, coming in `delay` seconds after its card. A span,
 *  so it may sit inside a line of text (`inline-block`). */
function In({
  delay,
  className,
  children,
}: {
  delay: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn("journey-in block", className)}
      style={{ "--d": `${delay}s` } as CSSProperties}
    >
      {children}
    </span>
  );
}

/** A grey line standing in for text. */
function Bar({ className }: { className?: string }) {
  return <span className={cn("block h-1.5 rounded-full bg-slate-200", className)} />;
}

/** The job these pictures follow, as a row: logo, title, company. */
function JobRow({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <FaviconLogo domain={followedJob.domain} className="size-8 rounded-lg" />
      <div className="min-w-0">
        <p className="text-ink truncate text-[13px] leading-tight font-semibold">
          {followedJob.title}
        </p>
        <p className="text-ink-meta text-[11px]">{followedJob.company}</p>
      </div>
    </div>
  );
}

const CARD = "rounded-2xl bg-white p-4 shadow-[var(--mk-shadow-float)]";

/**
 * Each step's picture: a piece of the app, drawn small, the way the step
 * ends for the Stripe application. Decorative, hidden from assistive
 * technology: the card's steps say the same.
 */
const PICTURES: Record<FeatureId, ReactNode> = {
  // The resume, with the keyword the student picked worked into a bullet.
  resumes: (
    <div className={CARD}>
      <div className="flex items-center justify-between">
        <span className="text-ink text-[13px] font-semibold">Alex Morgan</span>
        <In delay={0.9}>
          <span className="bg-advanced-tint text-advanced inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
            <SparkleIcon className="size-3" />
            Tailored for {followedJob.company}
          </span>
        </In>
      </div>
      <Bar className="mt-2 w-24" />
      <p className="text-ink-meta mt-4 text-[10px] font-semibold tracking-wide uppercase">
        Experience
      </p>
      <div className="mt-2 space-y-2">
        <Bar className="w-full" />
        <p className="text-ink-muted text-[11px] leading-snug">
          Built a grading dashboard in{" "}
          <In delay={0.5} className="inline-block">
            <span className="bg-positive-tint text-positive-ink rounded px-1 font-semibold">
              TypeScript
            </span>
          </In>{" "}
          and React for 300 students
        </p>
        <Bar className="w-5/6" />
        <Bar className="w-2/3" />
      </div>
    </div>
  ),
  // The posting's match: the ring fills to its score, the reasons beside it.
  matching: (
    <div className={CARD}>
      <JobRow />
      <div className="mt-4 flex items-center gap-4">
        <div className="relative size-16 shrink-0">
          <svg viewBox="0 0 36 36" className="size-16 -rotate-90">
            <circle
              cx="18"
              cy="18"
              r="15.5"
              fill="none"
              strokeWidth="3.5"
              className="stroke-border-strong"
            />
            <circle
              cx="18"
              cy="18"
              r="15.5"
              fill="none"
              strokeWidth="3.5"
              strokeLinecap="round"
              pathLength={100}
              strokeDasharray={`${followedJob.score} 100`}
              className="journey-ring stroke-positive"
              style={{ "--d": "0.3s" } as CSSProperties}
            />
          </svg>
          <span className="text-ink absolute inset-0 grid place-items-center text-base font-bold tabular-nums">
            {followedJob.score}
          </span>
        </div>
        <div className="flex-1 space-y-2">
          {[
            ["Skills", "w-[85%]", 0.5],
            ["Title", "w-[75%]", 0.65],
            ["Experience", "w-full", 0.8],
          ].map(([label, width, delay]) => (
            <div key={label as string}>
              <p className="text-ink-meta text-[10px] font-medium">{label}</p>
              <span className="mt-1 block h-1.5 rounded-full bg-slate-100">
                <span
                  className={cn("journey-grow bg-brand block h-full rounded-full", width as string)}
                  style={{ "--d": `${delay}s` } as CSSProperties}
                />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  ),
  // The application, filled field by field, waiting for the student's click.
  "auto-apply": (
    <div className={CARD}>
      <JobRow />
      <div className="mt-3 space-y-1.5">
        {[
          ["Full name", "Alex Morgan"],
          ["Email", "alex.morgan@university.edu"],
          ["Resume", "Alex_Morgan_Stripe.pdf"],
        ].map(([label, value], i) => (
          <In key={label} delay={0.3 + i * 0.35}>
            <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-2.5 py-1.5 ring-1 ring-slate-900/5">
              <span className="min-w-0">
                <span className="text-ink-meta block text-[9px]">{label}</span>
                <span className="text-ink block truncate text-[11px] font-medium">{value}</span>
              </span>
              <span className="bg-positive-ink grid size-4 shrink-0 place-items-center rounded-full text-white">
                <CheckIcon weight="bold" className="size-2.5" />
              </span>
            </div>
          </In>
        ))}
      </div>
      <In delay={1.5} className="relative mt-3 flex justify-end">
        <span className="bg-ink rounded-lg px-3 py-1.5 text-[11px] font-semibold text-white">
          Submit
        </span>
        <CursorIcon
          weight="fill"
          className="text-ink absolute -right-1 -bottom-3 size-5 drop-shadow"
        />
      </In>
    </div>
  ),
  // The tracker's card, marked applied, the sent resume kept with it.
  updates: (
    <div className={CARD}>
      <JobRow />
      <div className="mt-4 flex items-center gap-1.5">
        {(["Saved", "Applied", "Interviewing", "Offer"] as const).map((stage, i) => (
          <In key={stage} delay={0.3 + i * 0.15} className="flex-1">
            <span
              className={cn(
                "block rounded-full py-1 text-center text-[9px] font-semibold",
                i <= 1 ? "bg-brand text-white" : "text-ink-meta bg-slate-100",
              )}
            >
              {stage}
            </span>
          </In>
        ))}
      </div>
      <In
        delay={1}
        className="mt-3 flex items-center gap-2 rounded-lg bg-slate-50 px-2.5 py-2 ring-1 ring-slate-900/5"
      >
        <span className="bg-advanced-tint text-advanced grid size-6 place-items-center rounded-md text-[9px] font-bold">
          PDF
        </span>
        <span className="min-w-0">
          <span className="text-ink block truncate text-[11px] font-medium">
            Alex_Morgan_Stripe.pdf
          </span>
          <span className="text-ink-meta block text-[9px]">Sent resume · Applied Oct 1</span>
        </span>
      </In>
    </div>
  ),
};
