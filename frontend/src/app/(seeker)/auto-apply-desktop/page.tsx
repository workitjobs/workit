import {
  CheckCircleIcon,
  DownloadSimpleIcon,
  GoogleChromeLogoIcon,
  IdentificationCardIcon,
  LaptopIcon,
  ListChecksIcon,
} from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { ComponentType, ReactNode } from "react";

import { LightningRoundedIcon } from "@/components/custom-icons";
import { Logo } from "@/components/logo";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { EXTENSION_INSTALL_URL } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { AppWindowScene, EssayScene, FillingScene, QuestionScene, SubmitScene } from "./graphics";
import {
  DisclosureScene,
  DownloadScene,
  ScreenScene,
  SignInScene,
  StartScene,
  StoreScene,
} from "./setup-graphics";

export const metadata: Metadata = {
  title: "Auto Apply Desktop",
  description: "Download WorkIt Auto Apply, the desktop app that fills out your Auto Apply queue.",
};

/**
 * Where `WorkIt Auto Apply.dmg` downloads from, or null while there is no
 * build to download. W8 of docs/desktop_application_auto_apply.md makes the
 * signed, notarized DMG and puts it on Cloudflare R2; set its address here
 * then. While it is null, Download for Mac is drawn but cannot be pressed,
 * and the line under it says the download is coming.
 */
const DOWNLOAD_URL: string | null = null;

/** What the app needs (D17, D21 and W8 of the design doc), and its price
 *  (D6: a free beta with a daily Usage cap). */
const NEEDS: { Icon: ComponentType<{ className?: string }>; text: string }[] = [
  { Icon: LaptopIcon, text: "Apple Silicon Mac (M1 and later), macOS 13 or later" },
  { Icon: GoogleChromeLogoIcon, text: "Google Chrome" },
  { Icon: CheckCircleIcon, text: "Free during the beta, with a daily usage limit" },
];

/** The four moments of a run, in the order a run goes. The essays are
 *  written by the models behind WorkIt's Model route (D5 of the design doc),
 *  from the student's own experiences, in their voice. */
const MOMENTS: { title: string; body: string; scene: ReactNode }[] = [
  {
    title: "It Fills Out Each Form",
    body: "Each job opens in its own Chrome window, and the app fills out the form from your WorkIt profile and resume.",
    scene: <FillingScene />,
  },
  {
    title: "It Writes Your Essay Answers",
    body: "Questions like “Why do you want to work here?” get a personal answer, written from your own experiences and in your voice.",
    scene: <EssayScene />,
  },
  {
    title: "It Asks When It Needs You",
    body: "When a form asks something your profile doesn't answer, the question comes to the app's window. Pick an answer and it goes on.",
    scene: <QuestionScene />,
  },
  {
    title: "You Press Submit",
    body: "Each form stops on its last page. You look it over and press Submit. WorkIt never submits for you.",
    scene: <SubmitScene />,
  },
];

/**
 * The app's first run, as the Student build shows it (apply-agent's
 * first_run.py and app_window.py, section 3.1 of the design doc), in its
 * own words: its buttons are named as the app names them. Only what a
 * student does: no terminal, no developer checkout, and no code to paste
 * at sign-in, which WorkIt shows its admins only. The Worker extension
 * comes from the Chrome Web Store (W6, a v1 requirement), so step 5 is
 * Add to Chrome; the current build still asks for Developer mode and a
 * folder until the store copy is live. The Chrome check is the line under
 * the steps, since only a Mac without Chrome sees it.
 */
const SETUP: { title: string; body: string; optional?: boolean; scene: ReactNode }[] = [
  {
    title: "Download and Open the App",
    body: "Open WorkIt Auto Apply.dmg and drag the app to your Applications folder. The first time you open it, macOS asks if you want to open an app from the internet. Press Open.",
    scene: <DownloadScene />,
  },
  {
    title: "Sign In with WorkIt",
    body: "Press Sign In with WorkIt. Your browser opens WorkIt's sign-in page. Sign in the way you do on the website, then press Open WorkIt Auto Apply.",
    scene: <SignInScene />,
  },
  {
    title: "Read What Leaves Your Mac",
    body: "The app shows what it sends to WorkIt, to AI providers and to job sites, and what stays on your Mac. Press OK to accept its license.",
    scene: <DisclosureScene />,
  },
  {
    title: "Allow Screen Recording",
    body: "With it on, the app shows each form live and smoothly, so you can fix a form in the app's window. Press Allow, and macOS asks you one time. You can press Not Now instead.",
    optional: true,
    scene: <ScreenScene />,
  },
  {
    title: "Add the Worker Extension",
    body: "Press Set Up. Chrome opens on a profile that belongs to the app, separate from your own Chrome profiles. Click Add to Chrome, then confirm in Chrome's dialog. You do this one time, and it takes about a minute.",
    scene: <StoreScene />,
  },
  {
    title: "Start Applying",
    body: "The app shows your Auto Apply queue from WorkIt. Select the jobs you want, or paste a job link. Then press Start applying.",
    scene: <StartScene />,
  },
];

/**
 * /auto-apply-desktop — the page that promotes WorkIt Auto Apply, the
 * desktop app (KAN-723), and where a student downloads it (W8's download
 * page, KAN-835). It is the rail's row under Auto Apply
 * (../seeker-sidebar.tsx), at its own address, not under /auto-apply:
 * the Auto Apply row owns every path under its own, so both rows would
 * claim /auto-apply/desktop and only Auto Apply's would light.
 *
 * Mostly drawings, by design: a hero with the app's window and Download for
 * Mac, then one tile per moment of a run (./graphics.tsx). It reads
 * nothing, so it renders with no API call. Its copy follows what the app
 * does (docs/desktop_application_auto_apply.md, section 3): it fills each
 * form in its own Chrome window, writes its essay answers from the
 * student's experiences, asks the student what their profile doesn't
 * answer, and stops on each form's last page, where the student presses
 * Submit. So the page never says WorkIt applies or submits.
 *
 * Under the drawings, the setup (SETUP): what to have on WorkIt first, on
 * a violet band, then the app's first run, one numbered card per step,
 * each with that step's screen drawn on a violet stage
 * (./setup-graphics.tsx).
 *
 * The title is the bar's ("Auto Apply Desktop", ../bar-title.tsx), the
 * page's h1; the hero's headline and the setup's are h2s, and each tile's
 * and step's title an h3.
 */
export default function AutoApplyDesktopPage() {
  return (
    <div
      className={cn(
        "max-w-dashboard mx-auto flex w-full flex-1 flex-col gap-4 py-6",
        SEEKER_GUTTER,
      )}
    >
      <Card
        as="section"
        tone="tile"
        padding="none"
        aria-labelledby="desktop-hero"
        className="grid grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]"
      >
        <div className="flex flex-col justify-center p-6 sm:p-10 lg:p-12">
          <span className="bg-panel border-border-surface shadow-tile grid size-16 place-items-center rounded-[1.125rem] border">
            <Logo size="mark" decorative />
          </span>
          <h2 id="desktop-hero" className="text-hero text-ink mt-6 font-semibold text-balance">
            Let Your Mac Fill Out Your Applications
          </h2>
          <p className="text-subtitle text-ink-muted mt-4 max-w-lg font-normal">
            Our desktop app opens each job in its own Chrome window and fills out the application.
            Apply across multiple jobs, fill out all the personal questions. You check each one and
            press Submit.
          </p>

          <div className="mt-8">
            {DOWNLOAD_URL ? (
              <a href={DOWNLOAD_URL} download className={buttonClasses({ size: "lg" })}>
                <DownloadSimpleIcon />
                Download for Mac
              </a>
            ) : (
              <Button size="lg" disabled>
                <DownloadSimpleIcon />
                Download for Mac
              </Button>
            )}
            {!DOWNLOAD_URL && (
              <p className="text-body text-ink-meta mt-3">
                Coming soon. The download opens here when the app is ready.
              </p>
            )}
          </div>

          <ul className="text-body text-ink-meta mt-8 grid gap-2.5">
            {NEEDS.map(({ Icon, text }) => (
              <li key={text} className="flex items-center gap-2.5">
                <Icon aria-hidden className="size-4.5 shrink-0" />
                {text}
              </li>
            ))}
          </ul>
          <p className="text-body text-ink-meta mt-6">
            On Windows or an Intel Mac?{" "}
            <TextLink href={EXTENSION_INSTALL_URL} target="_blank" rel="noreferrer">
              Use the WorkIt extension for Chrome.
            </TextLink>
            .
          </p>
        </div>

        {/* The one bold block: the app's window on a violet stage. */}
        <div className="bg-brand flex items-center px-5 py-8 sm:px-10 sm:py-12 lg:px-12">
          <div className="mx-auto w-full max-w-2xl">
            <AppWindowScene />
          </div>
        </div>
      </Card>

      {/* Two by two from lg, so each drawing stays big; four across left
          the two Chrome windows of the first tile about 120px wide. */}
      <ol className="grid gap-4 lg:grid-cols-2">
        {MOMENTS.map(({ title, body, scene }) => (
          <Card as="li" key={title} padding="none" className="flex flex-col">
            <div className="bg-well m-2 flex min-h-80 items-center rounded-[0.5rem] px-6 py-6 lg:h-80 lg:py-0">
              <div className="mx-auto w-full max-w-lg">{scene}</div>
            </div>
            <div className="px-5 pt-3 pb-5">
              <h3 className="text-subtitle text-ink">{title}</h3>
              <p className="text-body text-ink-meta mt-1">{body}</p>
            </div>
          </Card>
        ))}
      </ol>

      <section aria-labelledby="desktop-setup" className="mt-6">
        <h2 id="desktop-setup" className="text-heading text-ink">
          Set Up WorkIt Auto Apply
        </h2>

        {/* What the app reads from WorkIt, before the first run's steps: a
            violet band, the hero's colour, so it reads as the way in. */}
        <div className="bg-brand text-on-brand mt-4 flex flex-col gap-5 rounded-[1.25rem] p-6 sm:flex-row sm:items-center sm:p-8">
          <span className="bg-panel/15 grid size-12 shrink-0 place-items-center rounded-2xl">
            <ListChecksIcon aria-hidden className="size-6" />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="text-subtitle">Before You Start</h3>
            <p className="text-body text-on-brand/85 mt-1 max-w-2xl">
              The app fills each form from your WorkIt profile, and it works through the jobs in
              your Auto Apply queue. Fill in Application Info and add jobs to your queue on WorkIt
              first.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <ButtonLink href="/auto-apply/info" variant="secondary" size="sm">
              <IdentificationCardIcon aria-hidden />
              Open Application Info
            </ButtonLink>
            <ButtonLink href="/auto-apply" variant="secondary" size="sm">
              <LightningRoundedIcon aria-hidden />
              Open Auto Apply
            </ButtonLink>
          </div>
        </div>

        <ol className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {SETUP.map(({ title, body, optional, scene }, i) => (
            <Card as="li" key={title} padding="none" className="flex flex-col">
              {/* The step's screen on a violet stage, its number on the
                  corner. Fixed from xl, where three share a row, so the
                  titles under them line up; below, it grows with its
                  drawing. */}
              <div className="bg-brand-tint relative m-2 flex min-h-52 items-center justify-center rounded-[0.5rem] px-6 py-7 xl:h-60 xl:py-0">
                <span
                  aria-hidden
                  className="bg-brand text-on-brand text-body absolute top-3 left-3 grid size-7 place-items-center rounded-full font-semibold"
                >
                  {i + 1}
                </span>
                {scene}
              </div>
              <div className="px-5 pt-3 pb-5">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-subtitle text-ink">{title}</h3>
                  {optional && (
                    <Badge variant="tag" tone="inert">
                      Optional
                    </Badge>
                  )}
                </div>
                <p className="text-body text-ink-meta mt-1">{body}</p>
              </div>
            </Card>
          ))}
        </ol>
        <p className="text-body text-ink-meta mt-4 flex items-center gap-2">
          <GoogleChromeLogoIcon aria-hidden className="size-4.5 shrink-0" />
          No Google Chrome? The app gives you a download link and continues when Chrome is
          installed.
        </p>
      </section>
    </div>
  );
}
