import { CheckIcon, FileTextIcon, XIcon } from "@phosphor-icons/react/ssr";

import { Logo } from "@/components/logo";
import { MatchGlyph } from "@/components/match-badge";
import { cn } from "@/lib/cn";
import { matchTier } from "@/lib/match";

import { Arrive } from "./arrive";
import { logoStrip, problems } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob } from "./feature-data";
import { CONTAINER, SectionHeading, StudioBox, studioGround, TYPE } from "./layout-parts";
import { delay, Panel } from "./scene-parts";

/**
 * Where applications get lost (KAN-923), right after the logo strip, so the
 * page says why before it says how: the user asked for the common problems
 * with applying, the hiring system's screen first, designed rather than set
 * as text. A centred chapter heading, then a bento of three
 * `.surface-card`s, each a scene in a `StudioBox` beside or over its copy:
 * the lead, a hiring system's screen marking the posting's keywords a
 * generic resume lacks, with WorkIt's keyword step laid over it; then the
 * same form typed again, and good jobs scattered across company job boards.
 * Each card says what goes wrong, then one line on what WorkIt does, after
 * the WorkIt mark. The scenes are mock UI in the app's own words and play
 * once as their card arrives (`Arrive`; the `.journey-*` classes in
 * landing.css), finished without script and with reduced motion.
 *
 * The scenes' sky is slate, not a feature's colour: this is the search as
 * it is, before WorkIt; the violet is WorkIt's own mark and checkboxes.
 * It replaced three pains set as plain text under hairlines, which the user
 * found boring. Copy, hedging and sources: `problems` in data.ts.
 */
const GROUND = studioGround({ glow: "var(--color-ink-meta)" });

export function Problems() {
  const { title, subtitle, screen, cards } = problems;
  return (
    <section aria-labelledby="problems-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <SectionHeading id="problems-title" title={title} subtitle={subtitle} />
        <div className="mt-12 grid gap-3 sm:mt-16">
          <Arrive className="surface-card grid gap-3 rounded-[1.75rem] p-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-6">
            <Copy
              title={screen.title}
              body={screen.body}
              fix={screen.fix}
              className="px-4 pt-4 pb-2 sm:px-6 sm:pt-6 lg:self-center lg:py-8"
            />
            <StudioBox ground={GROUND} className="p-4 sm:p-8 lg:p-10">
              <ScreenScene />
            </StudioBox>
          </Arrive>
          <div className="grid gap-3 md:grid-cols-2">
            {cards.map((card) => (
              <Arrive
                key={card.title}
                className="surface-card flex flex-col gap-3 rounded-[1.75rem] p-3"
              >
                <StudioBox ground={GROUND} className="h-80">
                  {card.scene === "forms" ? <FormsScene /> : <ScatteredScene />}
                </StudioBox>
                <Copy
                  title={card.title}
                  body={card.body}
                  fix={card.fix}
                  className="px-4 pt-3 pb-4 sm:px-6 sm:pb-6"
                />
              </Arrive>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/** A problem's copy: what goes wrong, then what WorkIt does about it. */
function Copy({
  title,
  body,
  fix,
  className,
}: {
  title: string;
  body: string;
  fix: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <h3 className={cn(TYPE.card, "text-ink text-balance")}>{title}</h3>
      <p className="text-ink-meta mt-3 text-pretty">{body}</p>
      <p className="text-ink mt-5 flex items-start gap-2.5 border-t border-slate-900/10 pt-4 text-[15px] text-pretty">
        <Logo size="mark" decorative className="mt-1 h-3.5" />
        <span>{fix}</span>
      </p>
    </div>
  );
}

/**
 * The lead scene: a hiring system's applicant screen reads one generic
 * resume against the posting's keywords, ticks the three it has, crosses
 * the three it lacks and does not move it forward; then WorkIt's keyword
 * step (Tailor's "Add the Keywords You Have Used") comes in over it, two of
 * the missing ones ticked and Kubernetes left out, since the student has
 * not used it. It shows the fix without promising the screen is passed.
 */
function ScreenScene() {
  const { role, keywords, used } = problems.screen;
  const found = keywords.filter((keyword) => keyword.found).length;
  const missing = keywords.filter((keyword) => !keyword.found);
  return (
    <div aria-hidden="true" className="mx-auto w-full max-w-[30rem]">
      <Panel className="overflow-hidden">
        <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3.5 py-2.5">
          <span className="flex gap-1">
            {[0, 1, 2].map((dot) => (
              <span key={dot} className="size-2 rounded-full bg-slate-900/15" />
            ))}
          </span>
          <span className="text-ink-muted ml-1.5 text-[11px] font-semibold">Applicant screen</span>
          <span className="text-ink-meta ml-auto truncate text-[11px]">{role}</span>
        </div>
        <div className="p-3.5 sm:p-4">
          <div className="flex items-center gap-2">
            <FileTextIcon className="text-ink-meta size-4 shrink-0" />
            <span className="text-ink text-[12px] font-semibold">resume.pdf</span>
            <span className="text-ink-meta ml-auto text-[11px] tabular-nums">
              {found} of {keywords.length} keywords
            </span>
          </div>
          <ul className="mt-3 flex flex-wrap gap-1.5">
            {keywords.map((keyword, i) => (
              <li
                key={keyword.word}
                className={cn(
                  "journey-in inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                  keyword.found
                    ? "bg-positive-tint text-positive-ink"
                    : "bg-danger-tint text-danger",
                )}
                style={delay(0.15 + i * 0.12)}
              >
                {keyword.found ? (
                  <CheckIcon weight="bold" className="size-3" />
                ) : (
                  <XIcon weight="bold" className="size-3" />
                )}
                {keyword.word}
              </li>
            ))}
          </ul>
          <div className="mt-4 flex items-center gap-3">
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-900/[0.08]">
              <span
                className="journey-grow bg-danger block h-full rounded-full"
                style={{ width: `${(found / keywords.length) * 100}%`, ...delay(0.9) }}
              />
            </span>
            <span
              className="journey-in bg-danger-tint text-danger shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold"
              style={delay(1.3)}
            >
              Not moved forward
            </span>
          </div>
        </div>
      </Panel>
      <div className="relative -mt-3 ml-auto w-[88%]">
        <Panel className="journey-in p-3.5 ring-1 ring-slate-900/5 sm:p-4" style={delay(1.8)}>
          <div className="flex items-center gap-2">
            <Logo size="mark" decorative className="h-3.5" />
            <span className="text-ink text-[12px] font-semibold">
              Add the Keywords You Have Used
            </span>
          </div>
          <ul className="mt-3 grid gap-1.5">
            {missing.map((keyword) => {
              const on = (used as readonly string[]).includes(keyword.word);
              return (
                <li key={keyword.word} className="flex items-center gap-2 text-[12px]">
                  <span
                    className={cn(
                      "grid size-4 shrink-0 place-items-center rounded-[5px]",
                      on ? "bg-brand text-white" : "ring-1 ring-slate-900/25 ring-inset",
                    )}
                  >
                    {on && <CheckIcon weight="bold" className="size-2.5" />}
                  </span>
                  <span className={on ? "text-ink" : "text-ink-meta"}>{keyword.word}</span>
                  {!on && <span className="text-ink-meta ml-auto text-[11px]">Not used</span>}
                </li>
              );
            })}
          </ul>
          <div className="mt-3 flex justify-end">
            <span className="bg-ink rounded-lg px-2.5 py-1 text-[11px] font-semibold text-white">
              Tailor Resume
            </span>
          </div>
        </Panel>
      </div>
    </div>
  );
}

/** The forms behind the front one, back to front: other companies, the same
 *  questions. */
const BEHIND = [
  { company: "Stripe", domain: "stripe.com" },
  { company: "Notion", domain: "notion.so" },
];

/** The front form's fields: the same three on every company's form. */
const FIELDS = [
  { label: "First name", value: "Alex" },
  { label: "School", value: "Northview University" },
  { label: "Why do you want to work here?", value: null },
];

/** How far each form sits from the one behind it, in px: a cascade of
 *  windows, so every form's company header shows. */
const STEP = 26;

/**
 * The same form, again: three companies' forms cascaded like windows, the
 * same fields on each, the front one filled in from the student's profile
 * and its written answer drafted, with Submit left to the student. Stacked
 * straight behind the front form, the other two showed only as slivers at
 * its edge and the repetition did not read.
 */
function FormsScene() {
  const offset = STEP * BEHIND.length;
  return (
    <div aria-hidden="true" className="absolute inset-0 grid place-items-center p-4">
      <div className="relative w-full max-w-[21rem]" style={{ paddingTop: offset }}>
        {BEHIND.map((form, i) => (
          <div
            key={form.company}
            className="absolute"
            style={{ top: i * STEP, left: i * STEP, right: offset - i * STEP }}
          >
            <Panel className="journey-in p-3" style={delay(0.1 + i * 0.15)}>
              <div className="flex items-center gap-2">
                <FaviconLogo domain={form.domain} className="size-5 rounded-md" />
                <span className="text-ink text-[12px] font-semibold">Apply to {form.company}</span>
              </div>
              <div className="mt-3 grid gap-2">
                {FIELDS.map((field) => (
                  <span key={field.label} className="bg-well block h-5 rounded-md" />
                ))}
              </div>
            </Panel>
          </div>
        ))}
        <div className="relative" style={{ marginLeft: offset }}>
          <Panel className="journey-in p-3.5" style={delay(0.45)}>
            <div className="flex items-center gap-2">
              <FaviconLogo domain="figma.com" className="size-5 rounded-md" />
              <span className="text-ink text-[12px] font-semibold">Apply to Figma</span>
            </div>
            <div className="mt-3 grid gap-2">
              {FIELDS.map((field, i) => (
                <div key={field.label}>
                  <p className="text-ink-meta text-[10px] font-medium">{field.label}</p>
                  <div
                    className="journey-in bg-brand-tint/60 mt-0.5 flex items-center gap-1.5 rounded-md px-2 py-1"
                    style={delay(0.9 + i * 0.25)}
                  >
                    {field.value ? (
                      <span className="text-ink text-[11px]">{field.value}</span>
                    ) : (
                      <span className="grid flex-1 gap-1 py-0.5">
                        <span className="bg-brand/30 block h-1.5 w-full rounded-full" />
                        <span className="bg-brand/30 block h-1.5 w-2/3 rounded-full" />
                      </span>
                    )}
                    <CheckIcon weight="bold" className="text-brand ml-auto size-3 shrink-0" />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex justify-end">
              <span className="text-ink rounded-lg px-2.5 py-1 text-[11px] font-semibold ring-1 ring-slate-900/20">
                Submit
              </span>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/** Where the employers' logos sit round the scene, in percent of its box,
 *  each a little turned, clear of the card in the middle. */
const SPOTS = [
  { x: 6, y: 10, r: -8 },
  { x: 28, y: 4, r: 6 },
  { x: 52, y: 8, r: -4 },
  { x: 76, y: 5, r: 9 },
  { x: 88, y: 30, r: -6 },
  { x: 84, y: 66, r: 5 },
  { x: 66, y: 84, r: -9 },
  { x: 40, y: 86, r: 7 },
  { x: 14, y: 80, r: -5 },
  { x: 3, y: 48, r: 8 },
];

/**
 * Good jobs, scattered: the employers of the logo strip strewn over the
 * scene, each its own company job board, and in the middle the one posting
 * that fits, the followed Stripe application, with its match in the app's
 * band, as the Jobs page puts the best fit first.
 */
function ScatteredScene() {
  const employers = logoStrip.employers.filter((employer) => employer.name !== followedJob.company);
  return (
    <div aria-hidden="true" className="relative h-full w-full">
      {SPOTS.map((spot, i) => {
        const employer = employers[i % employers.length];
        return (
          <span
            key={`${spot.x}-${spot.y}`}
            className="absolute"
            style={{ left: `${spot.x}%`, top: `${spot.y}%`, rotate: `${spot.r}deg` }}
          >
            <span className="journey-in block opacity-80" style={delay(0.08 * i)}>
              <FaviconLogo domain={employer.domain} className="size-9 sm:size-10" />
            </span>
          </span>
        );
      })}
      <div className="absolute top-1/2 left-1/2 w-[15rem] -translate-x-1/2 -translate-y-1/2">
        <Panel className="journey-in p-3.5" style={delay(1)}>
          <div className="flex items-center gap-2.5">
            <FaviconLogo domain={followedJob.domain} className="size-8" />
            <div className="min-w-0">
              <p className="text-ink truncate text-[12px] font-semibold">{followedJob.title}</p>
              <p className="text-ink-meta text-[11px]">{followedJob.company}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1.5">
            <MatchGlyph score={followedJob.score} />
            <span className="text-ink text-[11px] font-semibold">
              {matchTier(followedJob.score)}
            </span>
            <span className="text-ink-meta ml-auto text-[11px] tabular-nums">
              {followedJob.score}%
            </span>
          </div>
        </Panel>
      </div>
    </div>
  );
}
