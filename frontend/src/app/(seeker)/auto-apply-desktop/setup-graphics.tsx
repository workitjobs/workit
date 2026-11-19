import {
  ArrowRightIcon,
  ArrowUpRightIcon,
  CheckIcon,
  CursorIcon,
  FolderSimpleIcon,
  LockSimpleIcon,
  RecordIcon,
} from "@phosphor-icons/react/ssr";
import type { ReactNode } from "react";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

import { ChromeWindow, Monogram, TrafficLights } from "./graphics";

/**
 * One drawing per step of the setup (SETUP in ./page.tsx), each the screen
 * the student meets at that step, in the app's own words and button names
 * (apply-agent/src/apply/app_window.py's FIRST_RUN and SIGN_IN, and the
 * window's Start screen). Each sits on the step card's violet stage.
 *
 * Decoration only, as ./graphics.tsx's are: `aria-hidden`, no headings,
 * since the step's title and line say what it shows. Nothing moves.
 */

/** The app's icon: WorkIt's mark on a white squircle. */
function AppIcon({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "bg-panel border-border-surface shadow-tile grid size-14 place-items-center rounded-2xl border",
        className,
      )}
    >
      <Logo size="mark" decorative className="h-5" />
    </span>
  );
}

/** A small window of the app's: its title bar, then its screen. */
function MiniWindow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "bg-panel border-border-surface shadow-lift w-full max-w-64 overflow-hidden rounded-xl border",
        className,
      )}
    >
      <div className="border-border-subtle flex h-7 items-center border-b px-3">
        <TrafficLights />
      </div>
      <div className="p-3.5">{children}</div>
    </div>
  );
}

/** A button as the app draws one: brand-filled, or white with an edge. */
function FakeButton({ children, quiet }: { children: ReactNode; quiet?: boolean }) {
  return (
    <span
      className={cn(
        "text-note inline-flex h-8 items-center justify-center gap-1.5 rounded-md px-3 font-medium whitespace-nowrap",
        quiet ? "border-border-surface text-ink bg-panel border" : "bg-brand text-on-brand",
      )}
    >
      {children}
    </span>
  );
}

/** Step 1: the disk image's window, the app dragged onto Applications. */
export function DownloadScene() {
  return (
    <div aria-hidden className="flex w-full items-center justify-center gap-6 select-none">
      <div className="relative flex flex-col items-center gap-2">
        <AppIcon className="size-20 rounded-[1.375rem] [&_svg]:h-7" />
        <span className="text-body text-ink font-medium">WorkIt Auto Apply</span>
        <CursorIcon
          weight="fill"
          className="text-ink absolute top-15 left-[4.75rem] size-7 drop-shadow-[0_1px_0_white]"
        />
      </div>
      <ArrowRightIcon weight="bold" className="text-brand size-8 shrink-0" />
      <div className="flex flex-col items-center gap-2">
        <span className="bg-panel border-border-surface shadow-tile grid size-20 place-items-center rounded-[1.375rem] border">
          <FolderSimpleIcon weight="fill" className="text-brand size-11" />
        </span>
        <span className="text-body text-ink font-medium">Applications</span>
      </div>
    </div>
  );
}

/** Step 2: the app's sign-in screen, and the browser's page signed in. */
export function SignInScene() {
  return (
    <div aria-hidden className="relative w-full max-w-64 select-none">
      <MiniWindow>
        <p className="text-body text-ink font-semibold">Sign In to WorkIt Auto Apply</p>
        <p className="text-note text-ink-meta mt-1">
          Sign in with your WorkIt account in your browser.
        </p>
        <div className="mt-3">
          <FakeButton>Sign In with WorkIt</FakeButton>
        </div>
      </MiniWindow>
      <span className="bg-panel border-border-surface shadow-lift text-note text-ink absolute -right-3 -bottom-3 flex items-center gap-1.5 rounded-full border py-1.5 pr-3 pl-2 font-medium">
        <span className="bg-positive-tint text-positive-ink grid size-5 place-items-center rounded-full">
          <CheckIcon weight="bold" className="size-3" />
        </span>
        Signed in on WorkIt
      </span>
    </div>
  );
}

const SENDS = [
  { to: "WorkIt", tone: "bg-brand-tint text-brand-ink" },
  { to: "AI providers", tone: "bg-advanced-tint text-advanced" },
  { to: "Job sites", tone: "bg-positive-tint text-positive-ink" },
] as const;

/** Step 3: What Leaves Your Mac, where each thing goes, and OK. */
export function DisclosureScene() {
  return (
    <div aria-hidden className="w-full max-w-64 select-none">
      <MiniWindow>
        <p className="text-body text-ink font-semibold">What Leaves Your Mac</p>
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {SENDS.map(({ to, tone }) => (
            <li
              key={to}
              className={cn(
                "text-note flex items-center gap-1 rounded-full px-2 py-0.5 font-medium",
                tone,
              )}
            >
              <ArrowUpRightIcon weight="bold" className="size-3" />
              {to}
            </li>
          ))}
        </ul>
        <p className="text-note text-ink-meta mt-2 flex items-center gap-1.5">
          <LockSimpleIcon className="size-3.5 shrink-0" />
          Your records stay on your Mac.
        </p>
        <div className="mt-3">
          <FakeButton>OK</FakeButton>
        </div>
      </MiniWindow>
    </div>
  );
}

/** Step 4: the app's Allow Screen Recording screen. */
export function ScreenScene() {
  return (
    <div aria-hidden className="w-full max-w-64 select-none">
      <MiniWindow>
        <div className="flex items-center gap-2.5">
          <span className="bg-brand-tint text-brand grid size-8 shrink-0 place-items-center rounded-full">
            <RecordIcon weight="fill" className="size-4" />
          </span>
          <p className="text-body text-ink font-semibold">Allow Screen Recording</p>
        </div>
        <p className="text-note text-ink-meta mt-2">
          See each form live and smooth in the app&apos;s window.
        </p>
        <div className="mt-3 flex gap-2">
          <FakeButton>Allow</FakeButton>
          <FakeButton quiet>Not Now</FakeButton>
        </div>
      </MiniWindow>
    </div>
  );
}

/** Step 5: the Worker extension's Chrome Web Store page, the pointer on
 *  Add to Chrome. */
export function StoreScene() {
  return (
    <div aria-hidden className="relative w-full max-w-64 select-none">
      <ChromeWindow site="chromewebstore.google.com" tab="Chrome Web Store">
        <div className="p-3">
          <div className="flex items-center gap-2.5">
            <AppIcon className="size-9 rounded-lg [&_svg]:h-3.5" />
            <div className="min-w-0 flex-1">
              <p className="text-note text-ink truncate font-semibold">WorkIt Auto Apply Worker</p>
              <p className="text-note text-ink-meta">Extension</p>
            </div>
          </div>
          <div className="mt-2.5 flex justify-end">
            <FakeButton>Add to Chrome</FakeButton>
          </div>
        </div>
      </ChromeWindow>
      <CursorIcon
        weight="fill"
        className="text-ink absolute right-5 -bottom-2 size-6 drop-shadow-[0_1px_0_white]"
      />
    </div>
  );
}

const QUEUED = [
  { company: "Stripe", role: "Software Engineer Intern", tone: "brand" },
  { company: "Figma", role: "Software Engineer Intern", tone: "positive" },
] as const;

/** Step 6: the app's Start screen, the queue's jobs ticked. */
export function StartScene() {
  return (
    <div aria-hidden className="w-full max-w-64 select-none">
      <MiniWindow>
        <p className="text-body text-ink font-semibold">What should we apply to?</p>
        <ul className="mt-2 grid gap-1.5">
          {QUEUED.map(({ company, role, tone }) => (
            <li key={company} className="flex items-center gap-2">
              <span className="bg-brand text-on-brand grid size-4 shrink-0 place-items-center rounded">
                <CheckIcon weight="bold" className="size-3" />
              </span>
              <Monogram name={company} tone={tone} className="text-note size-6 rounded-md" />
              <span className="text-note text-ink min-w-0 truncate">
                <span className="font-semibold">{company}</span> {role}
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-3 [&>span]:w-full">
          <FakeButton>Start applying to 2 jobs</FakeButton>
        </div>
      </MiniWindow>
    </div>
  );
}
