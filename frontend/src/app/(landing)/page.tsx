import { DownloadSimpleIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { CSSProperties } from "react";

import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { cn } from "@/lib/cn";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";

import { SecondaryButton } from "./buttons";
import { Control } from "./control";
import { featuresIntro, hero, homeDescription, site, testimonial } from "./data";
import { GrowIn } from "./grow-in";
import { HeroGrid } from "./hero-board";
import { HiringGrid } from "./hiring-grid";
import { CONTAINER, PANEL, PANEL_INSET, SectionHeading, TYPE } from "./layout-parts";
import { LogoStrip } from "./logo-strip";
import { Problems } from "./problems";
import { FeatureJumps, ProductSections } from "./product-sections";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";
import { Testimonial } from "./testimonial";

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
 * (frontend/docs/home-page-review.md): the hero names the four features and
 * plays each one in a framed box, then each section leads into the next:
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
      {/* Hero: the first screen and nothing else. A rounded panel inset
          from the window, as every full-width band on these pages, the
          screen's height under the header (a minimum, so a screen too short
          for the headline grows the hero rather than clipping it), filled
          edge to edge by the tile grid (hero-board.tsx,
          .hero-grid): the headline in its large tile, the tiles of the jobs
          that fit lighting up round it. 5rem and 6.25rem are the header
          (72px, 76px from sm) and the panel's inset below it. */}
      <section className={PANEL_INSET}>
        <div
          className={cn(
            PANEL,
            "hero-ground relative isolate flex min-h-[calc(100svh-5rem)] flex-col overflow-hidden p-2 sm:min-h-[calc(100svh-6.25rem)] sm:p-3",
          )}
        >
          <HeroGrid>
            {/* From lg up the headline takes the screen's height into
                account (6.4svh, 44 to 72px), so it fits its tile's three
                rows on a short laptop screen (1024 × 768). */}
            <h1
              className={cn(
                TYPE.display,
                "hero-rise text-ink mx-auto max-w-4xl lg:text-[clamp(2.75rem,6.4svh,4.5rem)]",
              )}
              style={{ "--rd": ".15s" } as CSSProperties}
            >
              {hero.title}
            </h1>
            <p
              className={cn(TYPE.lead, "hero-rise text-ink-muted mx-auto mt-5 max-w-2xl")}
              style={{ "--rd": ".3s" } as CSSProperties}
            >
              {hero.subtitle}
            </p>
            {/* The sign-up pair, then Download for Mac (KAN-922) as a
                `SecondaryButton`, the same soft grey as the pair, only while
                there is a build. The row wraps, so the third button needs no
                other change. */}
            <div
              className="hero-rise mt-7 flex w-full flex-col flex-wrap items-center justify-center gap-3 sm:flex-row"
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
          </HeroGrid>
        </div>
      </section>

      {/* Real employers, drifting: logo-strip.tsx. */}
      <LogoStrip />

      {/* Applying as it is, before how WorkIt works: problems.tsx. */}
      <Problems />

      {/* WorkIt's answer to the problems: what it is, what "one place"
          means, and the four products as links to their sections below
          (FeatureJumps, product-sections.tsx). The turn from the problems to
          the product (the user's ask, 2026-11-20); it never promises replies
          or interviews. A tabs row over a large card was here, telling the
          four products' stories that the product sections tell again below,
          and the line under the heading repeated the hero's: both went with
          the web review. hero-features.tsx stays, unmounted. */}
      <section aria-labelledby="features-title" className="py-16 sm:py-24">
        <div className={CONTAINER}>
          <SectionHeading
            id="features-title"
            title={featuresIntro.title}
            subtitle={featuresIntro.subtitle}
          />
          <FeatureJumps />
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
