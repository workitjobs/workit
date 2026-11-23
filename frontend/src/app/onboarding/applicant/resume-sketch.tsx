import {
  BriefcaseIcon,
  CheckCircleIcon,
  CheckIcon,
  FileTextIcon,
  GraduationCapIcon,
  ScanIcon,
  WrenchIcon,
} from "@phosphor-icons/react/ssr";
import type { ComponentType, CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * Onboarding's right half once the student answers "Do you have a resume?"
 * (2026-11-17): a resume drawn as a sketch in Jake's layout, the template
 * WorkIt renders, with only the student's name in words and every other
 * line a bar, as the Generate loader's page is drawn
 * (`(seeker)/resumes/generate-running.tsx`). Two scenes on it:
 *
 *   upload  the student's resume read whole, on a 3.2s beat that loops:
 *           violet corners frame the page and breathe, a scan crosses it,
 *           every line flashes violet as the scan passes, and what WorkIt
 *           finds (Education, Experience, Skills) pops out beside it. The
 *           scan takes turns between two looks, a beat each
 *           (`ScanLooks`): a dot matrix with a shimmering wave, and a
 *           laser plane drawing a grid. A line sweeping down and back up
 *           read as a dull bar, and a diagonal band of light as out of
 *           place (2026-11-17).
 *   build   a resume being generated, once: a violet comet runs round the
 *           page's edge (one colour: violet into green read as random),
 *           the name types itself, each line is written in violet ink that
 *           settles to grey, and the tag above it, drawn as the landing
 *           tour's loader (a ring spinning round a page) on the app's own
 *           card, turns to a green "Resume ready" as the last line lands.
 *
 * The tag says what happens, never the template's name: "Building from
 * Jake's template" read as a label, not an action (2026-11-17). No sparkle
 * on the build: the builder calls no model, as Generate's loader says.
 *
 * Decoration (aria-hidden, as the panel is). CSS only, so the app's
 * reduced-motion rule ends each animation at once: the build page shows
 * written and ready, and the scan's looks are hidden.
 */

/** Jake's face, as the landing tour's resume sets it (`(landing)/
 *  resume-visual.tsx`, `JAKES_FACE`); copied, since importing it would
 *  load that client story with this page. */
const JAKES_FACE = '"Latin Modern Roman", "CMU Serif", "Computer Modern", Georgia, serif';

/** One entry: its bullets' widths, as shares of the column. */
type Entry = { bullets: number[] };
type Section =
  | {
      key: "education" | "experience" | "projects";
      kind: "entries";
      heading: number;
      entries: Entry[];
    }
  | { key: "skills"; kind: "skills"; heading: number; rows: number[] };

/** The page, top to bottom, in Jake's order. */
const SECTIONS: Section[] = [
  { key: "education", kind: "entries", heading: 26, entries: [{ bullets: [] }] },
  {
    key: "experience",
    kind: "entries",
    heading: 30,
    entries: [{ bullets: [94, 86, 70] }, { bullets: [90, 64] }],
  },
  { key: "projects", kind: "entries", heading: 24, entries: [{ bullets: [88, 76] }] },
  { key: "skills", kind: "skills", heading: 40, rows: [82, 68, 74] },
];

/** The contact line's bars, in px. */
const CONTACT = [38, 53, 43, 48];

/** How many bars the page draws, for the build's timing. */
const BARS =
  CONTACT.length +
  SECTIONS.reduce(
    (sum, s) =>
      sum +
      1 +
      (s.kind === "skills"
        ? s.rows.length * 2
        : s.entries.reduce((n, e) => n + 4 + e.bullets.length, 0)),
    0,
  );

/** The build's clock, in ms: the name types, then each bar starts a step
 *  after the last, and the page is done once the last bar's ink settles. */
const BARS_FROM = 750;
const BAR_STEP = 55;
const INK_MS = 900;
const DONE = BARS_FROM + (BARS - 1) * BAR_STEP + INK_MS;

/** The scan's beat, as `--animate-read` and the looks' animations set it. */
const BEAT = 3.2;

/** When the scan crosses a line at `y` (0 to 1 down the page), as a delay
 *  for its `read` flash, whose peak sits 8% into the beat. Both looks cross
 *  the page between 37.5% and 62.5% of the beat (globals.css), so height y
 *  at (y + 1.5) / 4 of it. */
const readDelay = (y: number) => `${(BEAT * ((y + 1.5) / 4 - 0.08)).toFixed(2)}s`;

/** What the scan finds, beside the section it was found in (`top`, px). */
const FOUND: { label: string; Icon: ComponentType<{ className?: string }>; top: number }[] = [
  { label: "Education", Icon: GraduationCapIcon, top: 92 },
  { label: "Experience", Icon: BriefcaseIcon, top: 168 },
  { label: "Skills", Icon: WrenchIcon, top: 352 },
];

/** A fade out at the build's end: `fade` played backwards, held. */
const fadeAtDone: CSSProperties = {
  animation: `fade 400ms var(--ease-exit) ${DONE}ms reverse both`,
};

/** A bar standing for a line of text. */
function Bar({
  width,
  tone,
  height = "h-1",
  order,
  mode,
}: {
  width: string;
  tone: string;
  height?: string;
  order: number;
  mode: "upload" | "build";
}) {
  const style: CSSProperties =
    mode === "build"
      ? { width, animationDelay: `${BARS_FROM + order * BAR_STEP}ms` }
      : { width, animationDelay: readDelay(0.08 + (0.85 * order) / (BARS - 1)) };
  return (
    <span
      className={cn(
        "block shrink-0 origin-left rounded-full",
        height,
        tone,
        mode === "build" ? "animate-ink" : "animate-read",
      )}
      style={style}
    />
  );
}

/** A brand colour at a share, for the scan's gradients. */
const brand = (share: number) => `color-mix(in oklab, var(--color-brand) ${share}%, transparent)`;

/** A dot every 12px, for the dot matrix. */
const DOTS = `radial-gradient(circle, ${brand(70)} 1.1px, transparent 1.6px)`;

/** The upload's two scan looks, over the page, taking turns a beat each
 *  (`animate-scan-phase`, delayed by a beat per look). Each crosses the
 *  page in the beat's middle quarter, as the lines flash. */
function ScanLooks() {
  const phase = (i: number): CSSProperties => ({ animationDelay: `${i * BEAT}s` });
  return (
    <span className="pointer-events-none absolute inset-0 motion-reduce:hidden">
      {/* 1. A dot matrix over the page, twinkling faintly, and a bright
          wave of the same dots running down it. */}
      <span className="animate-scan-phase absolute inset-0" style={phase(0)}>
        <span
          className="animate-twinkle absolute inset-0 opacity-45"
          style={{ backgroundImage: DOTS, backgroundSize: "12px 12px" }}
        />
        <span
          className="animate-dots-wave absolute inset-0"
          style={{
            backgroundImage: DOTS,
            backgroundSize: "12px 12px",
            maskImage: "linear-gradient(to bottom, transparent, black 45%, black 55%, transparent)",
            maskSize: "100% 40%",
            maskRepeat: "no-repeat",
          }}
        />
      </span>

      {/* 2. A laser plane running down the page, drawing a grid behind it
          that drains away once it reaches the foot. */}
      <span className="animate-scan-phase absolute inset-0" style={phase(1)}>
        <span
          className="animate-grid-wave absolute inset-0"
          style={{
            backgroundImage: `linear-gradient(${brand(28)} 1px, transparent 1px), linear-gradient(90deg, ${brand(28)} 1px, transparent 1px)`,
            backgroundSize: "16px 16px",
            maskImage: "linear-gradient(to bottom, transparent, black)",
            maskSize: "100% 50%",
            maskRepeat: "no-repeat",
          }}
        />
        <span className="animate-plane absolute inset-0">
          <span
            className="bg-brand absolute inset-x-0 top-0 h-0.5"
            style={{ boxShadow: `0 0 14px 3px ${brand(55)}, 0 -18px 24px -8px ${brand(25)}` }}
          />
        </span>
      </span>
    </span>
  );
}

/** The tag over the page: what is happening to it. */
function SceneTag({ mode }: { mode: "upload" | "build" }) {
  if (mode === "upload")
    return (
      <Tag>
        <span className="bg-brand-tint text-brand grid size-8 place-items-center rounded-lg">
          <ScanIcon weight="duotone" className="size-5" />
        </span>
        <TagWords title="Scanning your resume" line="Reading every section at once" />
      </Tag>
    );
  return (
    <Tag>
      {/* The tour's loader: a page with a ring spinning round it, then a
          green check as the last line lands. */}
      <span className="relative grid size-8 place-items-center">
        <span
          className="text-brand bg-panel ring-ink/5 absolute inset-0 grid place-items-center rounded-lg ring-1"
          style={fadeAtDone}
        >
          <FileTextIcon className="size-4" />
          <svg
            viewBox="0 0 32 32"
            className="absolute -inset-[3px] animate-spin [animation-duration:900ms]"
          >
            <circle
              cx="16"
              cy="16"
              r="14.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="22 70"
            />
          </svg>
        </span>
        <span
          className="bg-positive-tint text-positive-ink ring-positive/30 animate-pop absolute inset-0 grid place-items-center rounded-lg ring-1"
          style={{ animationDelay: `${DONE}ms` }}
        >
          <CheckIcon weight="bold" className="size-4" />
        </span>
      </span>
      {/* One line of words at a time, in one grid cell. */}
      <span className="grid">
        <span className="col-start-1 row-start-1" style={fadeAtDone}>
          <TagWords title="Generating your resume" line="Writing it from your answers" />
        </span>
        <span
          className="animate-rise col-start-1 row-start-1"
          style={{ animationDelay: `${DONE}ms` }}
        >
          <TagWords title="Resume ready" line="Yours to edit any time" />
        </span>
      </span>
    </Tag>
  );
}

function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="bg-panel border-border-surface shadow-lift animate-rise absolute top-0 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2.5 rounded-xl border py-2 pr-4 pl-2 whitespace-nowrap">
      {children}
    </span>
  );
}

function TagWords({ title, line }: { title: string; line: string }) {
  return (
    <span className="block font-sans">
      <span className="text-ink block text-sm font-semibold">{title}</span>
      <span className="text-ink-muted block text-xs">{line}</span>
    </span>
  );
}

/** NO WORDS BUT THE NAME (2026-11-17): the builder's answers were written
 *  on the page as they were typed, and students took the sketch for their
 *  real resume; the real one now opens in the editor once it exists. */
export function ResumeSketch({ mode, name }: { mode: "upload" | "build"; name: string }) {
  const building = mode === "build";
  // Each bar's place, top to bottom: the build's writing order and the
  // scan's height on the page.
  let order = 0;
  const bar = (width: string, tone: string, height?: string) => (
    <Bar key={order} width={width} tone={tone} height={height} order={order++} mode={mode} />
  );

  return (
    <div aria-hidden className="relative shrink-0 px-16 pt-12 pb-8">
      <SceneTag mode={mode} />

      <div className="relative">
        {/* Generating: a violet comet runs round the page until it is
            done. Scanning: violet corners frame it and breathe. */}
        {building ? (
          <span className="absolute -inset-[3px] overflow-hidden rounded-[9px]" style={fadeAtDone}>
            <span className="absolute -inset-1/2 animate-spin bg-[conic-gradient(from_0deg,transparent_0_50%,color-mix(in_oklab,var(--color-brand)_25%,transparent)_75%,var(--color-brand)_100%)] [animation-duration:2.4s]" />
          </span>
        ) : (
          <span className="animate-focus absolute -inset-4 opacity-60">
            {[
              "top-0 left-0 border-t-[3px] border-l-[3px] rounded-tl-xl",
              "top-0 right-0 border-t-[3px] border-r-[3px] rounded-tr-xl",
              "bottom-0 left-0 border-b-[3px] border-l-[3px] rounded-bl-xl",
              "bottom-0 right-0 border-r-[3px] border-b-[3px] rounded-br-xl",
            ].map((corner) => (
              <span key={corner} className={cn("border-brand absolute size-9", corner)} />
            ))}
          </span>
        )}

        <div
          className="bg-panel shadow-lift relative flex h-[440px] w-[340px] flex-col overflow-hidden rounded-md px-7 pt-8 pb-6"
          style={{ fontFamily: JAKES_FACE }}
        >
          {/* The heading: the name in words, the contact line as bars. */}
          {/* The name types on its own box, so a centred name reveals from
              its first letter, not from the column's left edge. */}
          <p className="text-ink text-center text-[22px] leading-tight font-bold">
            <span
              className={cn(
                "inline-block max-w-full truncate align-top",
                building && "animate-type",
              )}
            >
              {name}
            </span>
          </p>
          <div className="mt-2 flex items-center justify-center gap-1.5">
            {CONTACT.map((width, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="bg-ink/20 h-2 w-px" />}
                {bar(`${width}px`, "bg-ink/25")}
              </span>
            ))}
          </div>

          {SECTIONS.map((section, s) => (
            <div key={s} className="mt-4">
              {/* A heading over its rule, as Jake's small caps sit. */}
              {bar(`${section.heading}%`, "bg-ink/60", "h-1.5")}
              <span className="bg-ink/50 mt-1 block h-px w-full" />
              {section.kind === "entries" ? (
                section.entries.map((entry, e) => {
                  return (
                    <div key={e} className="mt-2.5">
                      <div className="flex items-center justify-between gap-6">
                        {bar("46%", "bg-ink/45", "h-1.5")}
                        {bar("18%", "bg-ink/25")}
                      </div>
                      <div className="mt-1.5 flex items-center justify-between gap-6">
                        {bar("34%", "bg-ink/20")}
                        {bar("14%", "bg-ink/15")}
                      </div>
                      {entry.bullets.map((width) => (
                        <div
                          key={`${e}-${width}`}
                          className="mt-1.5 flex items-center gap-1.5 pl-2"
                        >
                          <span className="bg-ink/30 size-1 shrink-0 rounded-full" />
                          {bar(`${width}%`, "bg-ink/15")}
                        </div>
                      ))}
                    </div>
                  );
                })
              ) : (
                <div className="mt-2.5 flex flex-col gap-1.5">
                  {section.rows.map((width) => (
                    <div key={width} className="flex items-center gap-2">
                      {bar("16%", "bg-ink/40")}
                      {bar(`${width - 16}%`, "bg-ink/15")}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          {!building && <ScanLooks />}
        </div>
      </div>

      {/* What the scan found, popping out over the page's right edge. */}
      {!building &&
        FOUND.map(({ label, Icon, top }, i) => (
          <span
            key={label}
            className="bg-panel shadow-lift text-ink animate-pop absolute right-0 flex items-center gap-1.5 rounded-full py-1 pr-3 pl-1.5 font-sans text-xs font-medium"
            style={{ top: top + 48, animationDelay: `${800 + i * 700}ms` }}
          >
            <span className="bg-brand-tint text-brand grid size-5 place-items-center rounded-full">
              <Icon className="size-3" />
            </span>
            {label}
            <CheckCircleIcon weight="fill" className="text-positive size-3.5" />
          </span>
        ))}
    </div>
  );
}
