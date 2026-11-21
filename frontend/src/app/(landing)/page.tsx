import { DownloadSimpleIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { CSSProperties } from "react";

import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { cn } from "@/lib/cn";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";

import { SecondaryButton } from "./buttons";
import { Control } from "./control";
import { featuresIntro, hero, homeDescription, site, testimonial } from "./data";
import { DraftLines } from "./draft-lines";
import { GrowIn } from "./grow-in";
import { HeroMosaic } from "./hero-mosaic";
import { HiringGrid } from "./hiring-grid";
import { CONTAINER, PANEL, PANEL_INSET, SectionHeading, TYPE } from "./layout-parts";
import { LogoStrip } from "./logo-strip";
import { Problems } from "./problems";
import { FeatureJumps, ProductSections } from "./product-sections";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";
import { Testimonial } from "./testimonial";
import { WhatIs } from "./what-is";
import { WhyExists } from "./why-exists";

/** The home page's link preview has room for the whole tagline. */
const shareTitle = `${site.name}: ${site.tagline}`;

export const metadata: Metadata = {
  title: { absolute: `${site.name} · ${site.tabTitle}` },
  description: homeDescription,
  alternates: { canonical: "/" },
  openGraph: { ...SHARE_DEFAULTS, url: "/", title: shareTitle, description: homeDescription },
  twitter: {
    card: "summary_large_image",
    title: shareTitle,
    description: homeDescription,
    images: [SHARE_IMAGE],
  },
};

/**
 * The page at /, redesigned in KAN-923 after Calendly's home page
 * (frontend/docs/home-page-review.md) and being redrawn section by section
 * in the makeover's tile system (frontend/docs/home-page-makeover-brief.md,
 * direction E; the hero is the first section done): the hero shows the
 * four parts of a search coming together, then each section leads into the next:
 * proof the jobs are real (the logo strip), where applications get lost
 * (the problems), the four features, each product in depth, what stays
 * the student's call (control) and where the jobs come from (hiring
 * systems), which runs into the footer. The FAQ went on 2026-11-19 (the
 * user's call); its questions are on the Help Center's page. Every
 * animation sits in a `StudioBox`; only the product sections pin. The
 * scenes this replaced (the city hero, the bridge, the pinned tour, the 3D
 * pipeline, the applications route) and three the user took out on
 * 2026-11-19 (the statement and the journey, archived; the closing call
 * to action, deleted) are off the page; the archived ones' files stay. Every call to
 * action leads into the app's own sign-up, log-in or OAuth flow.
 */
export default function LandingPage() {
  return (
    <main id="main" className="flex-1">
      {/* Hero: the first screen (the makeover's direction E, 2026-11-20). A
          grey panel inset from the window, as every full-width band on these
          pages, at least the screen's height under the header (5rem and
          6.25rem are the header, 72px and 76px from sm, and the panel's
          inset below it). From lg up the words stand on the left and the
          mosaic on the right (hero-mosaic.tsx): the four parts of a search
          as tiles that snap together round WorkIt's icon. Below lg the
          words are centred over the mosaic. The mosaic's side follows the
          screen's height and width, so both fit one screen from 1024 × 768. */}
      <section className={PANEL_INSET}>
        <div
          className={cn(
            PANEL,
            "grid min-h-[calc(100svh-5rem)] items-center gap-10 overflow-hidden bg-(--mk-mist) px-5 py-10 sm:min-h-[calc(100svh-6.25rem)] sm:px-10 lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-12 lg:px-14 lg:py-8 xl:gap-16 xl:px-20",
          )}
        >
          <div className="mx-auto w-full max-w-xl text-center lg:mx-0 lg:text-left">
            {/* From lg up the headline takes the screen's height into
                account (7.6svh, 48 to 72px), so it fits beside the mosaic
                on a short laptop screen (1024 × 768) and stands three
                lines tall in its column on a larger one. */}
            <h1
              className={cn(TYPE.display, "hero-rise text-ink lg:text-[clamp(3rem,7.6svh,4.5rem)]")}
              style={{ "--rd": ".15s" } as CSSProperties}
            >
              {hero.title}
            </h1>
            <p
              className={cn(TYPE.lead, "hero-rise text-ink-muted mt-5")}
              style={{ "--rd": ".3s" } as CSSProperties}
            >
              {hero.subtitle}
            </p>
            {/* The sign-up pair, then Download for Mac (KAN-922) as a
                `SecondaryButton`, the same soft grey as the pair, only while
                there is a build. The row wraps, so the third button needs no
                other change. */}
            <div
              className="hero-rise mt-7 flex w-full flex-col flex-wrap items-center justify-center gap-3 sm:flex-row lg:justify-start"
              style={{ "--rd": ".4s" } as CSSProperties}
            >
              <SocialSignUpButton provider="google" onGrey />
              <SocialSignUpButton provider="linkedin_oidc" onGrey />
              {DESKTOP_DOWNLOAD_URL && (
                <SecondaryButton href={site.download.href}>
                  <DownloadSimpleIcon aria-hidden className="size-5" />
                  Download for Mac
                </SecondaryButton>
              )}
              <div className="w-full text-center sm:basis-full lg:text-left">
                <EmailSignUpLink />
              </div>
            </div>
          </div>
          <HeroMosaic className="mx-auto w-full max-w-[26rem] lg:mx-0 lg:w-[min(32.5rem,calc(100svh-15rem),40vw)] lg:max-w-none" />
        </div>
      </section>

      {/* Real employers, drifting: logo-strip.tsx. */}
      <LogoStrip />

      {/* The opening run after Loopsii's (the user's ask, 2026-11-20): what
          WorkIt is, then the problems on a dark band that zooms in as it
          rises, then why WorkIt exists over the product demo. */}
      <WhatIs />

      {/* Applying as it is, before how WorkIt works: problems.tsx. */}
      <Problems />

      <WhyExists />

      {/* WorkIt's answer to the problems: one app for every step, wherever
          the student starts, and the four products, each with its selling
          line, as links to their sections below (FeatureJumps,
          product-sections.tsx), framed like every section. The turn from the
          problems to the product (the user's ask, 2026-11-20); it never
          promises replies or interviews. A tabs row over a large card was
          here, telling the four products' stories that the product sections
          tell again below, and the line under the heading repeated the
          hero's: both went with the web review. hero-features.tsx stays,
          unmounted. */}
      <section aria-labelledby="features-title" className="py-16 sm:py-24">
        <div className={CONTAINER}>
          <div className="relative">
            <DraftLines gap="1.5rem" />
            <SectionHeading
              id="features-title"
              title={featuresIntro.title}
              subtitle={featuresIntro.subtitle}
            />
            <FeatureJumps />
          </div>
        </div>
      </section>

      {/* Each product in depth, from its feature page: product-sections.tsx. */}
      <ProductSections />

      {/* What WorkIt will never do without you: control.tsx. */}
      <Control />

      {/* Where the jobs come from. The Features menu's foot row links here. */}
      <HiringGrid />

      {/* Testimonial, read word by word: testimonial.tsx. Hidden until a
          real quote replaces the placeholder (`testimonial.show`). */}
      {testimonial.show && (
        <section className={cn(PANEL_INSET, "mt-2 sm:mt-6")}>
          <GrowIn className={cn(PANEL, "bg-surface py-20 sm:py-28")}>
            <div className={CONTAINER}>
              <Testimonial />
            </div>
          </GrowIn>
        </section>
      )}
    </main>
  );
}
