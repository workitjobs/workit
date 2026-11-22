import {
  ArrowCounterClockwiseIcon,
  CheckIcon,
  PencilSimpleLineIcon,
} from "@phosphor-icons/react/ssr";

import { cn } from "@/lib/cn";

import { Arrive } from "./arrive";
import { control } from "./data";
import { DraftLines } from "./draft-lines";
import { FaviconLogo } from "./favicon-logo";
import { CONTAINER, SectionHeading, StudioBox, studioGround, TYPE } from "./layout-parts";
import { delay, Panel } from "./scene-parts";

/**
 * The promises behind the product (KAN-923), after the product sections:
 * the worry any tool that writes for you raises (will it make things up,
 * will it write over me?) answered as what WorkIt does, each promise a
 * scene from the app's own screens: a centred chapter heading, then two
 * `.surface-card`s side by side, each scene over its copy. They play once
 * as their card arrives (`Arrive`, the `.journey-*` classes), finished
 * without script and with reduced motion. It had four, led by "You click
 * Submit, every time" with "Five at a time, never a flood" last; both went
 * with the web review (2026-11-20), since Auto Apply's product section
 * says them just above.
 *
 * The scenes' sky is WorkIt's violet, where the problems' above are slate:
 * the search as it is, then WorkIt's answer. It replaced four cards of an
 * icon and two lines, which the user found undesigned. Copy and sources:
 * `control` in data.ts.
 */
const GROUND = studioGround({ glow: "var(--color-brand)" });

export function Control() {
  const { title, subtitle, promises } = control;
  return (
    <section aria-labelledby="control-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <SectionHeading id="control-title" title={title} subtitle={subtitle} />
        <div className="relative mt-10 grid gap-3 sm:mt-14 md:grid-cols-2">
          <DraftLines gap="1.25rem" />
          {promises.map((promise) => (
            <Arrive
              key={promise.title}
              className="surface-card flex flex-col gap-3 rounded-[1.75rem] p-3"
            >
              <StudioBox ground={GROUND} className="grid h-72 place-items-center p-5">
                {promise.scene === "truth" ? <TruthScene /> : <WordsScene />}
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
