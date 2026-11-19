import {
  ArrowCounterClockwiseIcon,
  CheckIcon,
  PaperclipIcon,
  PencilSimpleLineIcon,
} from "@phosphor-icons/react/ssr";

import { cn } from "@/lib/cn";

import { Arrive } from "./arrive";
import { control } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob } from "./feature-data";
import { CONTAINER, SectionHeading, StudioBox, studioGround, TYPE } from "./layout-parts";
import { delay, Panel } from "./scene-parts";

/**
 * The promises behind the product (KAN-923), after the product sections:
 * the worry any auto apply tool raises (will it send things for me, make
 * things up, flood employers?) answered as what WorkIt does, each promise a
 * scene from the app's own screens. A centred chapter heading, then the
 * lead promise as a wide `.surface-card` (the filled form waiting for the
 * student's own Submit, their cursor on it) and the other three in a row
 * of cards, each scene over its copy. They play once as their card
 * arrives (`Arrive`, the `.journey-*` classes), finished without script
 * and with reduced motion.
 *
 * The scenes' sky is WorkIt's violet, where the problems' above are slate:
 * the search as it is, then WorkIt's answer. It replaced four cards of an
 * icon and two lines, which the user found undesigned. Copy and sources:
 * `control` in data.ts.
 */
const GROUND = studioGround({ glow: "var(--color-brand)" });

export function Control() {
  const { title, subtitle, promises } = control;
  const [lead, ...rest] = promises;
  return (
    <section aria-labelledby="control-title" className="py-20 sm:py-28">
      <div className={CONTAINER}>
        <SectionHeading id="control-title" title={title} subtitle={subtitle} />
        <div className="mt-12 grid gap-3 sm:mt-16">
          <Arrive className="surface-card grid gap-3 rounded-[1.75rem] p-3 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-6">
            <StudioBox ground={GROUND} className="p-6 sm:p-10">
              <SubmitScene />
            </StudioBox>
            <Copy
              title={lead.title}
              body={lead.body}
              className="px-4 pt-3 pb-4 sm:px-6 sm:pb-6 lg:self-center lg:py-8"
            />
          </Arrive>
          <div className="grid gap-3 lg:grid-cols-3">
            {rest.map((promise) => (
              <Arrive
                key={promise.title}
                className="surface-card flex flex-col gap-3 rounded-[1.75rem] p-3"
              >
                <StudioBox ground={GROUND} className="grid h-72 place-items-center p-5">
                  {promise.scene === "truth" ? (
                    <TruthScene />
                  ) : promise.scene === "words" ? (
                    <WordsScene />
                  ) : (
                    <FiveScene />
                  )}
                </StudioBox>
                <Copy
                  title={promise.title}
                  body={promise.body}
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

function Copy({ title, body, className }: { title: string; body: string; className?: string }) {
  return (
    <div className={className}>
      <h3 className={cn(TYPE.card, "text-ink text-balance")}>{title}</h3>
      <p className="text-ink-meta mt-3 text-pretty">{body}</p>
    </div>
  );
}

/** The followed application's form, filled in from the student's profile. */
const FIELDS = [
  { label: "Full name", value: "Alex Morgan" },
  { label: "Resume", value: "Alex_Morgan_Stripe.pdf", file: true },
  { label: `Why ${followedJob.company}?`, value: null },
];

/**
 * The lead: the followed application's form, every field filled, the
 * written answer drafted and the tailored resume attached, its status
 * Ready to Submit (Up Next's word for it), and the student's own cursor,
 * named "You", on the company's Submit button. WorkIt never presses it.
 */
function SubmitScene() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-[28rem]">
      <Panel className="journey-in overflow-hidden" style={delay(0.1)}>
        <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-4 py-3">
          <FaviconLogo domain={followedJob.domain} className="size-6 rounded-md" />
          <span className="text-ink text-[13px] font-semibold">Apply to {followedJob.company}</span>
          <span className="text-ink-meta ml-auto truncate text-[11px]">{followedJob.title}</span>
        </div>
        <div className="grid gap-2.5 p-4">
          {FIELDS.map((field, i) => (
            <div key={field.label}>
              <p className="text-ink-meta text-[10px] font-medium">{field.label}</p>
              <div
                className="journey-in bg-well mt-1 flex items-center gap-2 rounded-md px-2.5 py-1.5"
                style={delay(0.35 + i * 0.25)}
              >
                {field.file && <PaperclipIcon className="text-ink-meta size-3.5 shrink-0" />}
                {field.value ? (
                  <span className="text-ink truncate text-[12px]">{field.value}</span>
                ) : (
                  <span className="grid flex-1 gap-1 py-0.5">
                    <span className="block h-1.5 w-full rounded-full bg-slate-900/15" />
                    <span className="block h-1.5 w-4/5 rounded-full bg-slate-900/15" />
                  </span>
                )}
                <CheckIcon weight="bold" className="text-positive-ink ml-auto size-3.5 shrink-0" />
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 border-t border-slate-900/[0.06] px-4 py-3">
          <span
            className="journey-in bg-positive-tint text-positive-ink inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold"
            style={delay(1.15)}
          >
            <CheckIcon weight="bold" className="size-3" />
            Ready to Submit
          </span>
          <span className="bg-ink ml-auto rounded-lg px-3.5 py-1.5 text-[12px] font-semibold text-white">
            Submit
          </span>
        </div>
      </Panel>
      {/* The student's cursor, named as a shared cursor is, on Submit. */}
      <span
        className="journey-in absolute flex items-start gap-1"
        // The pointer's tip on the middle of Submit (the footer's right
        // end, 14px up from the panel's foot).
        style={{ left: "calc(100% - 3.6rem)", top: "calc(100% - 1.8rem)", ...delay(1.55) }}
      >
        <svg viewBox="0 0 14 20" className="h-5 w-3.5 drop-shadow-sm">
          <path
            d="M1 1v15l4-3.6 2.7 5.6 2.4-1.1-2.6-5.5H13z"
            className="fill-ink stroke-white"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
        </svg>
        <span className="bg-brand mt-3 rounded-full px-2 py-0.5 text-[10px] font-semibold text-white">
          You
        </span>
      </span>
    </div>
  );
}

/**
 * Nothing invented: the tailored resume in the editor, one line reworded
 * from the student's own bullet and marked, with its Undo, as Tailor marks
 * every change; the bullet it came from, struck, above it. Every number and
 * tool in the new wording was in the bullet or the bank.
 */
function TruthScene() {
  return (
    <Panel aria-hidden="true" className="journey-in w-full max-w-[19rem] p-4" style={delay(0.1)}>
      <p className="text-ink text-center text-[13px] font-semibold">Alex Morgan</p>
      <p className="text-ink-meta mt-3 border-b border-slate-900/10 pb-1 text-[9px] font-semibold tracking-[0.08em] uppercase">
        Projects
      </p>
      <p className="text-ink mt-2 text-[11px] font-semibold">Budget Tracker</p>
      <p className="text-ink-meta mt-1 text-[10px] leading-snug line-through decoration-slate-400">
        Made a budget app with React for 200 students
      </p>
      <div
        className="journey-in mt-1.5 flex items-start gap-2 rounded-lg bg-white"
        style={delay(0.7)}
      >
        <p className="text-ink min-w-0 flex-1 text-[11px] leading-snug">
          <span className="bg-advanced-tint rounded-[3px] px-0.5">
            Built a budget tracker in React used by 200 students
          </span>
        </p>
      </div>
      <div className="journey-in mt-3 flex items-center justify-between" style={delay(1.1)}>
        <span className="text-ink-meta text-[10px]">1 change</span>
        <span className="text-ink inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-slate-900/15">
          <ArrowCounterClockwiseIcon className="size-3" />
          Undo
        </span>
      </div>
    </Panel>
  );
}

/**
 * Your words win: a written question in a form, the student's own answer
 * typed over the draft, marked as theirs and kept for the next form that
 * asks it.
 */
function WordsScene() {
  return (
    <Panel aria-hidden="true" className="journey-in w-full max-w-[19rem] p-4" style={delay(0.1)}>
      <div className="flex items-center gap-2">
        <FaviconLogo domain="figma.com" className="size-5 rounded-md" />
        <span className="text-ink text-[12px] font-semibold">Apply to Figma</span>
      </div>
      <p className="text-ink-meta mt-3 text-[10px] font-medium">Why do you want to work here?</p>
      <div className="ring-brand mt-1 rounded-lg p-2.5 ring-2">
        <p className="text-ink text-[11px] leading-snug">
          I designed every screen of my budget app in Figma, and I want to help build the tool that
          taught me how.
          <span className="bg-brand ml-0.5 inline-block h-3 w-px translate-y-0.5 align-baseline" />
        </p>
      </div>
      <div className="journey-in mt-3 flex items-center gap-2" style={delay(0.8)}>
        <span className="bg-brand-tint text-brand-ink inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
          <PencilSimpleLineIcon className="size-3" />
          Your words
        </span>
        <span className="text-ink-meta ml-auto inline-flex items-center gap-1 text-[10px]">
          <CheckIcon weight="bold" className="text-positive-ink size-3" />
          Kept for next time
        </span>
      </div>
    </Panel>
  );
}

/** Five tabs, each filling one application, in Up Next's own states. */
const TABS = [
  { company: "Stripe", domain: "stripe.com", state: "ready" },
  { company: "Databricks", domain: "databricks.com", state: "filling" },
  { company: "Duolingo", domain: "duolingo.com", state: "needs" },
  { company: "Figma", domain: "figma.com", state: "filling" },
  { company: "Notion", domain: "notion.so", state: "ready" },
] as const;

const STATES = {
  ready: { label: "Ready to Submit", className: "bg-positive-tint text-positive-ink" },
  filling: { label: "Filling", className: "bg-advanced-tint text-advanced" },
  needs: { label: "Needs You", className: "bg-warning-tint text-warning" },
};

/**
 * Five at a time: Up Next's In Progress group, five applications, each in
 * its own tab, in the queue's own states (auto-apply/queue-table.tsx):
 * Ready to Submit, Filling, Needs You. Never more than five.
 */
function FiveScene() {
  return (
    <Panel aria-hidden="true" className="journey-in w-full max-w-[19rem] p-3" style={delay(0.1)}>
      <div className="flex items-center justify-between px-1">
        <span className="text-ink text-[12px] font-semibold">In Progress</span>
        <span className="text-ink-meta text-[10px] tabular-nums">5 of 5 tabs</span>
      </div>
      <ul className="mt-2 grid gap-1.5">
        {TABS.map((tab, i) => {
          const state = STATES[tab.state];
          return (
            <li
              key={tab.company}
              className="journey-in bg-well flex items-center gap-2 rounded-lg px-2 py-1.5"
              style={delay(0.3 + i * 0.15)}
            >
              <FaviconLogo domain={tab.domain} className="size-5 rounded-md" />
              <span className="text-ink text-[11px] font-medium">{tab.company}</span>
              <span
                className={cn(
                  "ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold",
                  state.className,
                )}
              >
                {state.label}
              </span>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
