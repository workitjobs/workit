import type { Metadata } from "next";
import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";

import { faqs, hero, site, testimonial } from "./data";
import { FaqList } from "./faq-list";
import { FocusIn } from "./focus-in";
import { GrowIn } from "./grow-in";
import { HeroGrid } from "./hero-board";
import { HeroFeatures } from "./hero-features";
import { HiringGrid } from "./hiring-grid";
import { Journey } from "./journey";
import { CONTAINER, PANEL, PANEL_INSET, SectionHeading, TYPE } from "./layout-parts";
import { LogoStrip } from "./logo-strip";
import { ProductSections } from "./product-sections";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";
import { Testimonial } from "./testimonial";

/** The home page's link preview has room for the whole tagline. */
const shareTitle = `${site.name}: ${site.tagline}`;

export const metadata: Metadata = {
  title: { absolute: `${site.name} · ${site.tabTitle}` },
  description: hero.subtitle,
  alternates: { canonical: "/" },
  openGraph: { ...SHARE_DEFAULTS, url: "/", title: shareTitle, description: hero.subtitle },
  twitter: {
    card: "summary_large_image",
    title: shareTitle,
    description: hero.subtitle,
    images: [SHARE_IMAGE],
  },
};

/**
 * The page at /, redesigned in KAN-923 after Calendly's home page
 * (frontend/docs/home-page-review.md): the hero names the four features and
 * plays each one in a framed box, then each section leads into the next:
 * proof the jobs are real (the logo strip), one application through the
 * four steps (the journey), each product in depth, where the jobs come
 * from (hiring systems) and the FAQ, which runs into the footer. Every
 * animation sits in a `StudioBox`; only the product sections pin. The
 * scenes this replaced (the city hero, the bridge, the pinned tour, the 3D
 * pipeline, the applications route) and two the user took out on
 * 2026-11-19 (the statement, archived; the closing call to action,
 * deleted) are off the page; the statement's files stay. Every call to
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
            {/* The sign-up pair. A Download for Mac button (KAN-922) joins
                this row: it wraps, so a third button needs no other change. */}
            <div
              className="hero-rise mt-7 flex w-full flex-col flex-wrap items-center justify-center gap-3 sm:flex-row"
              style={{ "--rd": ".4s" } as CSSProperties}
            >
              <SocialSignUpButton provider="google" />
              <SocialSignUpButton provider="linkedin_oidc" />
              <div className="w-full text-center sm:basis-full">
                <EmailSignUpLink />
              </div>
            </div>
          </HeroGrid>
        </div>
      </section>

      {/* Real employers, drifting: logo-strip.tsx. */}
      <LogoStrip />

      {/* The four features, one at a time: a section of their own since the
          hero became one screen (hero-features.tsx). On the plain white
          page with no label above the heading: on the hero's violet panel,
          with a violet eyebrow, it read as off (the user's call). */}
      <section aria-labelledby="features-title" className="py-16 sm:py-24">
        <div className={CONTAINER}>
          <SectionHeading id="features-title" title="Every step of the search, in one place" />
          <div className="mt-10 sm:mt-14">
            <HeroFeatures />
          </div>
        </div>
      </section>

      {/* One application through the four steps: journey.tsx. */}
      <Journey />

      {/* Each product in depth, from its feature page: product-sections.tsx. */}
      <ProductSections />

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

      {/* FAQ: the questions rise in one after another once the list is on
          screen, in time (FocusIn, landing.css). From lg up the heading
          holds on the left while the questions pass on the right. */}
      <section id="faq" className="py-20 sm:py-28">
        <div
          className={cn(
            CONTAINER,
            "lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start lg:gap-16",
          )}
        >
          <div className="lg:sticky lg:top-32">
            <FocusIn>
              <SectionHeading
                align="left"
                className="max-lg:mx-auto max-lg:text-center"
                title="Questions, answered"
              />
            </FocusIn>
          </div>
          <FocusIn>
            <FaqList items={faqs} className="faq-rise mt-12 lg:mt-0 lg:max-w-none" />
          </FocusIn>
        </div>
      </section>
    </main>
  );
}
