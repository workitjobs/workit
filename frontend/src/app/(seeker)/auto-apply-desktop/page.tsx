import {
  DownloadSimpleIcon,
  IdentificationCardIcon,
  ListChecksIcon,
} from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";

import { AppWindowScene } from "@/components/auto-apply-desktop/graphics";
import { DesktopNeeds } from "@/components/auto-apply-desktop/needs";
import { LightningRoundedIcon } from "@/components/custom-icons";
import { Logo } from "@/components/logo";
import { Button, ButtonLink, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { DESKTOP_DOWNLOAD_URL, DESKTOP_PAGE } from "@/lib/auto-apply-desktop";
import { EXTENSION_INSTALL_URL } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";

export const metadata: Metadata = {
  title: "Auto Apply Desktop",
  description: "Download WorkIt Auto Apply, the desktop app that fills out your Auto Apply queue.",
};

/** Focus on a button that sits on a `bg-brand` surface. */
const BAND_FOCUS =
  "focus-visible:ring-on-brand focus-visible:ring-offset-2 focus-visible:ring-offset-brand";

/**
 * /auto-apply-desktop — where a signed-in student downloads WorkIt Auto
 * Apply, the Mac app (KAN-723), and does what the app needs on WorkIt
 * first. The top bar's Download App and Up Next's offer open it, on a Mac
 * once there is a build (KAN-922); it has no rail row. Its own address,
 * not /auto-apply/desktop: the Auto Apply row owns every path under its
 * own, and would light there.
 *
 * The pitch, what a run does tile by tile, is the public download page's
 * (app/(landing)/download/), linked under the hero. This page keeps to
 * the download and the steps on the website: Application Info and the
 * queue, which the app reads at sign-in. The app walks the student
 * through the rest itself the first time it opens (section 3.1 of
 * docs/desktop_application_auto_apply.md), so the page names that and
 * does not copy its screens: a copy here drifts from the app.
 *
 * The title is the bar's ("Auto Apply Desktop", ../bar-title.tsx), the
 * page's h1; the hero's headline and the setup's are h2s.
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
            Our desktop app opens each job in its own Chrome window and fills out the application,
            personal questions too. You check each one and press Submit.
          </p>

          <div className="mt-8">
            {DESKTOP_DOWNLOAD_URL ? (
              <a href={DESKTOP_DOWNLOAD_URL} download className={buttonClasses({ size: "lg" })}>
                <DownloadSimpleIcon />
                Download for Mac
              </a>
            ) : (
              <>
                <Button size="lg" disabled>
                  <DownloadSimpleIcon />
                  Download for Mac
                </Button>
                <p className="text-body text-ink-meta mt-3">
                  Coming soon. The download opens here when the app is ready.
                </p>
              </>
            )}
          </div>

          <DesktopNeeds className="text-body text-ink-meta mt-8" />
          <p className="text-body text-ink-meta mt-6">
            On Windows or an Intel Mac?{" "}
            <TextLink href={EXTENSION_INSTALL_URL} target="_blank" rel="noreferrer">
              Use the WorkIt extension for Chrome
            </TextLink>
            .
          </p>
          {DESKTOP_DOWNLOAD_URL && (
            <p className="text-body text-ink-meta mt-2">
              <TextLink href={DESKTOP_PAGE}>See what the app does</TextLink>
            </p>
          )}
        </div>

        {/* The one bold block: the app's window on a violet stage. */}
        <div className="bg-brand flex items-center px-5 py-8 sm:px-10 sm:py-12 lg:px-12">
          <div className="mx-auto w-full max-w-2xl">
            <AppWindowScene />
          </div>
        </div>
      </Card>

      <section aria-labelledby="desktop-setup" className="mt-6">
        <h2 id="desktop-setup" className="text-heading text-ink">
          Set Up WorkIt Auto Apply
        </h2>

        {/* What the app reads from WorkIt, before its first run: a violet
            band, the hero's colour, so it reads as the way in. */}
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
          {/* A white focus ring with a violet gap: the buttons' own ring is
              brand, the band's colour, and showed nothing on Tab. */}
          <div className="flex shrink-0 flex-wrap gap-2">
            <ButtonLink
              href="/auto-apply/info"
              variant="secondary"
              size="sm"
              className={BAND_FOCUS}
            >
              <IdentificationCardIcon aria-hidden />
              Open Application Info
            </ButtonLink>
            <ButtonLink href="/auto-apply" variant="secondary" size="sm" className={BAND_FOCUS}>
              <LightningRoundedIcon aria-hidden />
              Open Auto Apply
            </ButtonLink>
          </div>
        </div>

        <p className="text-body text-ink-meta mt-4 max-w-3xl">
          Then download the app and open it. The first time, it walks you through signing in with
          WorkIt, what it sends and what stays on your Mac, and adding its Chrome extension. It
          takes a few minutes.
        </p>
      </section>
    </div>
  );
}
