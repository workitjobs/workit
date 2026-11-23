import {
  ArrowSquareOutIcon,
  CheckIcon,
  CursorIcon,
  GearSixIcon,
  LockSimpleIcon,
  MagnifyingGlassIcon,
  PaperclipIcon,
} from "@phosphor-icons/react/ssr";
import type { CSSProperties, ReactNode } from "react";

import { SparkleIcon } from "@/components/sparkle-icon";
import { cn } from "@/lib/cn";

/**
 * The page's drawings of WorkIt Auto Apply (./page.tsx): its window, the
 * Chrome windows it fills forms in, a question it asks and a form's last
 * page. Each is drawn from the app's own window (apply-agent/window/src:
 * app.tsx and cards.tsx) with the same words, so a change there that
 * changes what the student sees changes these too.
 *
 * Every drawing is decoration: `aria-hidden`, with no heading, since the
 * copy beside it says what it shows and a mock heading would break the
 * page's heading order (frontend/CLAUDE.md, KAN-560). The one motion is
 * each progress bar drawing itself out once as the page loads
 * (`animate-draw-x`); globals.css ends it at once under reduced motion.
 */

/** macOS's own close, minimise and zoom colours, on every window drawn here. */
const TRAFFIC_LIGHTS = ["#ff5f57", "#febc2e", "#28c840"];

export function TrafficLights() {
  return (
    <span className="flex shrink-0 gap-1.5">
      {TRAFFIC_LIGHTS.map((colour) => (
        <span key={colour} className="size-2.5 rounded-full" style={{ background: colour }} />
      ))}
    </span>
  );
}

const MONOGRAM_TONES = {
  brand: "bg-brand-tint text-brand-ink",
  positive: "bg-positive-tint text-positive-ink",
  warning: "bg-warning-tint text-warning",
} as const;

/** A company's tile: its first letter on a tint, for a drawing that loads no logo. */
export function Monogram({
  name,
  tone,
  className,
}: {
  name: string;
  tone: keyof typeof MONOGRAM_TONES;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "text-body rounded-control grid size-8 shrink-0 place-items-center font-semibold",
        MONOGRAM_TONES[tone],
        className,
      )}
    >
      {name[0]}
    </span>
  );
}

/** A bar that draws itself out to `share` once, `delay` ms after load. */
function Progress({ share, delay = 0 }: { share: number; delay?: number }) {
  const style: CSSProperties = { width: `${share}%`, animationDelay: `${delay}ms` };
  return (
    <span className="bg-border block h-1 overflow-hidden rounded-full">
      <span
        className="bg-brand animate-draw-x block h-full origin-left rounded-full"
        style={style}
      />
    </span>
  );
}

function Check({ children }: { children: ReactNode }) {
  return (
    <li className="text-ink-muted flex items-center gap-2.5">
      <span className="bg-positive-tint text-positive-ink grid size-4.5 shrink-0 place-items-center rounded-full">
        <CheckIcon weight="bold" className="size-3" />
      </span>
      {children}
    </li>
  );
}

/** A Chrome window: its tab strip and address bar, then the page. */
export function ChromeWindow({
  site,
  tab,
  children,
  className,
}: {
  site: string;
  tab: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "bg-panel border-border-surface shadow-lift overflow-hidden rounded-xl border",
        className,
      )}
    >
      <div className="bg-well flex h-8 items-end gap-3 px-3">
        <span className="self-center">
          <TrafficLights />
        </span>
        <span className="bg-panel text-note text-ink-muted truncate rounded-t-lg px-3 py-1.5">
          {tab}
        </span>
      </div>
      <div className="border-border-subtle flex h-8 items-center border-b px-3">
        <span className="bg-well text-note text-ink-meta flex h-6 min-w-0 flex-1 items-center gap-1.5 rounded-full px-3">
          <LockSimpleIcon className="size-3 shrink-0" />
          <span className="truncate">{site}</span>
        </span>
      </div>
      {children}
    </div>
  );
}

/** One question of a job form, answered: its label, then the answer in its box. */
function FilledField({ label, value, file }: { label: string; value: string; file?: boolean }) {
  return (
    <div>
      <p className="text-note text-ink-meta">{label}</p>
      <p className="border-border-control text-note text-ink mt-1 flex h-8 items-center gap-1.5 rounded-md border px-2.5">
        {file && <PaperclipIcon className="text-ink-meta size-3.5 shrink-0" />}
        <span className="truncate">{value}</span>
        {file && (
          <CheckIcon weight="bold" className="text-positive-ink ml-auto size-3.5 shrink-0" />
        )}
      </p>
    </div>
  );
}

/**
 * The hero's drawing: WorkIt Auto Apply's window on a run, in front of one
 * of the Chrome windows it fills forms in. The window is the app's board
 * (app.tsx's Home): today's usage, the to-do on top (a form ready to
 * submit, cards.tsx's Submit) and the jobs it is still working on.
 */
export function AppWindowScene() {
  return (
    // Padding, not the front window's margin, sets the two apart: a first
    // child's top margin collapses out through this box and moved both.
    <div aria-hidden className="relative pt-28 select-none sm:pt-24">
      {/* The Chrome window behind, where the form on top is filled. */}
      <ChromeWindow
        site="job-boards.greenhouse.io/stripe"
        tab="Stripe: Software Engineer Intern"
        className="absolute top-0 right-0 w-[78%]"
      >
        <div className="grid gap-3 px-5 pt-4 pb-24">
          <p className="text-body text-ink font-semibold">Apply for this job</p>
          <div className="grid grid-cols-2 gap-3">
            <FilledField label="First Name" value="Alex" />
            <FilledField label="Last Name" value="Rivera" />
          </div>
          <FilledField label="Resume" value="Alex Rivera Resume.pdf" file />
        </div>
      </ChromeWindow>

      {/* WorkIt Auto Apply's own window, in front. */}
      <div className="bg-app border-border-surface shadow-lift relative z-10 w-full overflow-hidden rounded-xl border sm:w-[88%]">
        <div className="border-border-subtle bg-panel flex h-11 items-center gap-3 border-b px-3.5">
          <TrafficLights />
          <span className="text-note text-ink flex items-center gap-1.5 font-semibold">
            <span className="bg-brand text-on-brand text-meta grid size-5 place-items-center rounded-md">
              W
            </span>
            WorkIt Auto Apply
          </span>
          <span className="text-note text-ink-meta ml-auto hidden items-center gap-3 sm:flex">
            <span className="flex items-center gap-1">
              <MagnifyingGlassIcon className="size-3.5" /> Find jobs
            </span>
            <span>Applied</span>
            <span className="flex items-center gap-1">
              <GearSixIcon className="size-3.5" /> Settings
            </span>
          </span>
        </div>

        <div className="px-5 pt-4 pb-5">
          <div className="text-note text-ink-meta flex items-baseline justify-between gap-4">
            <span>Today&apos;s usage</span>
            <span>24% used · resets at 4:00 PM</span>
          </div>
          <div className="mt-1.5">
            <Progress share={24} />
          </div>

          <p className="text-title text-ink mt-5">1 application ready to submit</p>

          <div className="bg-panel border-border-surface shadow-panel mt-3 rounded-2xl border px-4.5 py-4">
            <div className="flex items-center gap-3">
              <Monogram name="Stripe" tone="brand" />
              <div className="min-w-0">
                <p className="text-body text-ink font-semibold">Stripe</p>
                <p className="text-note text-ink-meta truncate">Software Engineer Intern</p>
              </div>
            </div>
            <p className="text-subtitle text-ink mt-3.5">Take a quick look</p>
            <ul className="text-body mt-2 grid gap-1.5">
              <Check>All 14 questions answered</Check>
              <Check>Checked against your WorkIt profile</Check>
              <Check>Resume attached</Check>
            </ul>
            <span className="bg-brand text-on-brand text-note rounded-control mt-3.5 inline-flex h-9 items-center gap-1.5 px-3.5 font-medium">
              Open form to submit
              <ArrowSquareOutIcon className="size-3.5" />
            </span>
          </div>

          <p className="text-note text-ink-meta mt-5 font-semibold">Still working on</p>
          <WorkingRow name="Figma" role="Software Engineer Intern" tone="positive" share={62} />
          <WorkingRow
            name="Ramp"
            role="Product Engineer, New Grad"
            tone="warning"
            share={35}
            delay={150}
          />
          <p className="text-note text-ink-meta pt-1.5">and 3 more waiting to start</p>
        </div>
      </div>
    </div>
  );
}

/** A row of "Still working on". Only "Filling out" is drawn: the app shows
 *  "Checking answers" with a sweep of no length, which a still drawing
 *  cannot say. */
function WorkingRow({
  name,
  role,
  tone,
  share,
  delay = 0,
}: {
  name: string;
  role: string;
  tone: keyof typeof MONOGRAM_TONES;
  share: number;
  delay?: number;
}) {
  return (
    <div className="flex items-center gap-3 py-2">
      <Monogram name={name} tone={tone} />
      <div className="min-w-0 flex-1">
        <p className="text-body text-ink font-semibold">{name}</p>
        <p className="text-note text-ink-meta truncate">{role}</p>
      </div>
      <div className="w-28 shrink-0 text-right">
        <p className="text-note text-ink-meta">Filling out</p>
        <div className="mt-1.5">
          <Progress share={share} delay={delay} />
        </div>
      </div>
    </div>
  );
}

/** The first tile: two Chrome windows, each filling its own form at once. */
export function FillingScene() {
  return (
    <div aria-hidden className="grid w-full grid-cols-2 gap-3 select-none">
      <MiniForm
        name="Figma"
        site="jobs.ashbyhq.com"
        tone="positive"
        fields={[
          ["Full Name", "Alex Rivera"],
          ["School", "UCLA"],
        ]}
        share={62}
      />
      <MiniForm
        name="Ramp"
        site="jobs.lever.co"
        tone="warning"
        fields={[
          ["Graduation", "June 2027"],
          ["Sponsorship", "No"],
        ]}
        share={35}
        delay={200}
      />
    </div>
  );
}

function MiniForm({
  name,
  site,
  tone,
  fields,
  share,
  delay,
}: {
  name: string;
  site: string;
  tone: keyof typeof MONOGRAM_TONES;
  fields: [string, string][];
  share: number;
  delay?: number;
}) {
  return (
    <ChromeWindow site={site} tab={name}>
      <div className="grid gap-2.5 p-3">
        <div className="flex items-center gap-2">
          <Monogram name={name} tone={tone} className="text-note size-6 rounded-md" />
          <span className="text-note text-ink font-semibold">{name}</span>
        </div>
        {fields.map(([label, value]) => (
          <FilledField key={label} label={label} value={value} />
        ))}
        <div>
          <p className="text-note text-ink-meta">Filling out</p>
          <div className="mt-1">
            <Progress share={share} delay={delay} />
          </div>
        </div>
      </div>
    </ChromeWindow>
  );
}

/**
 * The second tile: an essay question in a form's own box, the answer
 * written into it from the student's experiences (the Figma club project
 * is one of Alex's, like UCLA in the first tile), stopped mid-sentence with
 * a still caret. The line under the box carries the AI mark, `SparkleIcon`.
 * The answer names nothing about the company beyond what its posting
 * says: company facts wait on W9 of the design doc.
 */
export function EssayScene() {
  return (
    <div aria-hidden className="w-full select-none">
      <ChromeWindow site="jobs.ashbyhq.com/figma" tab="Figma: Software Engineer Intern">
        <div className="p-4">
          <p className="text-body text-ink font-semibold">Why do you want to work at Figma?</p>
          <p className="border-border-control text-body text-ink-muted mt-2 rounded-md border px-3 py-2.5 leading-relaxed">
            Last spring I led four friends in rebuilding our club&apos;s event app, and we planned
            every screen together in one Figma file. Watching four people shape one design at once,
            with no one waiting on anyone, made me want to build
            <span className="bg-brand ml-0.5 inline-block h-4 w-0.5 translate-y-0.5" />
          </p>
          <p className="text-note text-brand-ink mt-2.5 flex items-center gap-1.5 font-medium">
            <SparkleIcon className="size-3.5 shrink-0" />
            Written from your experiences, in your voice
          </p>
        </div>
      </ChromeWindow>
    </div>
  );
}

/** The third tile: a question the student's profile doesn't answer, as
 *  the app's question card asks it, with one option picked. */
export function QuestionScene() {
  return (
    <div aria-hidden className="w-full select-none">
      <p className="text-subtitle text-ink">1 quick question for you</p>
      <div className="bg-panel border-border-surface shadow-lift mt-3 rounded-2xl border p-4">
        <div className="flex items-center gap-3">
          <Monogram name="Ramp" tone="warning" />
          <div className="min-w-0">
            <p className="text-body text-ink font-semibold">Ramp</p>
            <p className="text-note text-ink-meta truncate">Product Engineer, New Grad</p>
          </div>
        </div>
        <p className="text-body text-ink mt-3.5 font-semibold">
          Are you open to working in New York?
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <span className="border-brand bg-brand-tint text-brand-ink text-body rounded-control flex h-10 items-center justify-center border font-medium">
            Yes
          </span>
          <span className="border-border-surface text-ink text-body rounded-control flex h-10 items-center justify-center border font-medium">
            No
          </span>
        </div>
      </div>
    </div>
  );
}

/** The fourth tile: the form's last page, the student's pointer on its Submit. */
export function SubmitScene() {
  return (
    <div aria-hidden className="relative w-full select-none">
      <ChromeWindow site="job-boards.greenhouse.io/stripe" tab="Stripe">
        <div className="grid gap-2.5 p-4">
          <p className="text-body text-ink font-semibold">Review your application</p>
          <ul className="text-note grid gap-1.5">
            <Check>Contact details</Check>
            <Check>Resume and education</Check>
            <Check>Written answers</Check>
          </ul>
          <span className="bg-brand text-on-brand text-body rounded-control mt-1 flex h-10 items-center justify-center font-medium">
            Submit Application
          </span>
        </div>
      </ChromeWindow>
      <CursorIcon
        weight="fill"
        className="text-ink absolute right-[30%] bottom-1 size-7 drop-shadow-[0_1px_0_white]"
      />
    </div>
  );
}
