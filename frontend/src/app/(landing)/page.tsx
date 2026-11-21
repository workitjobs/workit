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
import { HeroPipeline } from "./hero-pipeline";
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
 * since (frontend/docs/home-page-makeover-brief.md says what was tried):
 * the hero shows the whole pipeline as four cells of the drafting grid,
 * then each section leads into the next:
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
      {/* TEMPORARY (2026-11-21): `/?intro=b` plays the second entrance, for
          the user to compare (landing.css, "TEMPORARY"). It writes only to
          <html>, whose attributes hydration does not check. */}
      <script
        dangerouslySetInnerHTML={{
          __html:
            "try{var v=new URLSearchParams(location.search).get('intro');if(v)document.documentElement.dataset.intro=v}catch(e){}",
        }}
      />
      {/* Hero (redrawn 2026-11-21): the first screen, on the page's own
          white ground, in the drafting grid's frame, the page's first, so
          its side lines start the rail every section below continues. The
          headline, its line and the sign-up pair are centred, and under
          them the whole pipeline stands as four cells of the grid
          (hero-pipeline.tsx): one application, from the resume to the
          tracker. The frame hangs from the header: its top edge is the
          header's foot line (header.tsx draws it), so the section has no
          padding above. It fills the screen's height under the header
          (4.5rem, 4.75rem from sm; 58rem at most, so a tall screen does
          not stretch it), the headline centred in the room above the
          pipeline, so the logo strip starts below the first screen. */}
      <section className="flex min-h-[min(calc(100svh-4.5rem),58rem)] flex-col pb-10 sm:min-h-[min(calc(100svh-4.75rem),58rem)]">
        <div className={cn(CONTAINER, "flex flex-1 flex-col")}>
          <div className="relative flex flex-1 flex-col">
            <DraftLines gap="1.5rem" first />
            <div className="relative mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center py-10 text-center">
              {/* From lg up the headline takes the screen's height into
                  account (7.4svh, 48 to 72px), so its two lines and the
                  pipeline fit one screen on a short laptop (1024 × 768). */}
              <h1
                className={cn(
                  TYPE.display,
                  "hero-reveal text-ink lg:text-[clamp(3rem,7.4svh,4.5rem)]",
                )}
                style={{ "--rd": ".15s" } as CSSProperties}
              >
                {hero.title}
              </h1>
              <p
                className={cn(TYPE.lead, "hero-reveal text-ink-muted mx-auto mt-5 max-w-2xl")}
                style={{ "--rd": ".3s" } as CSSProperties}
              >
                {hero.subtitle}
              </p>
              {/* The sign-up pair, then Download for Mac (KAN-922) as a
                  `SecondaryButton`, the same soft grey as the pair, only
                  while there is a build. The row wraps, so the third button
                  needs no other change. */}
              <div
                className="hero-reveal mt-7 flex w-full flex-col flex-wrap items-center justify-center gap-3 sm:flex-row"
                style={{ "--rd": ".4s" } as CSSProperties}
              >
                <SocialSignUpButton provider="google" />
                <SocialSignUpButton provider="linkedin_oidc" />
                {DESKTOP_DOWNLOAD_URL && (
                  <SecondaryButton href={site.download.href}>
                    <DownloadSimpleIcon aria-hidden className="size-5" />
                    Download for Mac
                  </SecondaryButton>
                )}
                <div className="w-full text-center sm:basis-full">
                  <EmailSignUpLink />
                </div>
              </div>
            </div>
            <HeroPipeline />
          </div>
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
