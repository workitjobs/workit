import type { Metadata } from "next";
import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";

import { ClosingCta } from "./closing-cta";
import { closing, faqs, hero, site, testimonial } from "./data";
import { Statement } from "./deferred-sections";
import { FaqList } from "./faq-list";
import { backdrop } from "./features/catalog";
import { FocusIn } from "./focus-in";
import { GrowIn } from "./grow-in";
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
 * proof the jobs are real (the logo strip), why it matters (the statement),
 * one application through the four steps (the journey), each product in
 * depth, where the jobs come from (hiring systems), the FAQ and the close.
 * Every animation sits in a `StudioBox`; nothing pins to the screen. The
 * scenes this replaced (the city hero, the bridge, the pinned tour, the 3D
 * pipeline, the applications route) stay in the folder, unmounted. Every
 * call to action leads into the app's own sign-up, log-in or OAuth flow.
 */
export default function LandingPage() {
  return (
    <main id="main" className="flex-1">
      {/* Hero, in a rounded panel inset from the window, like every
          full-width band on these pages, on the brand's mesh (.hero-mesh). */}
      <section className={PANEL_INSET}>
        <div
          className={cn(
            PANEL,
            "hero-mesh relative isolate overflow-hidden pb-3 sm:pb-6",
          )}
        >
          <div className={cn(CONTAINER, "pt-14 text-center sm:pt-20 lg:pt-24")}>
            <p
              className="hero-rise text-ink inline-flex items-center rounded-full bg-white/60 px-3.5 py-1.5 text-sm font-medium ring-1 ring-white/80"
              style={{ "--rd": ".05s" } as CSSProperties}
            >
              {hero.audience}
            </p>
            <h1
              className={cn(TYPE.display, "hero-rise text-ink mx-auto mt-6 max-w-4xl")}
              style={{ "--rd": ".15s" } as CSSProperties}
            >
              {hero.title}
            </h1>
            <p
              className={cn(TYPE.lead, "hero-rise text-ink-muted mx-auto mt-6 max-w-2xl")}
              style={{ "--rd": ".3s" } as CSSProperties}
            >
              {hero.subtitle}
            </p>
            {/* The sign-up pair. A Download for Mac button (KAN-922) joins
                this row: it wraps, so a third button needs no other change. */}
            <div
              className="hero-rise mt-8 flex flex-col flex-wrap items-center justify-center gap-3 sm:flex-row"
              style={{ "--rd": ".4s" } as CSSProperties}
            >
              <SocialSignUpButton provider="google" />
              <SocialSignUpButton provider="linkedin_oidc" />
              <div className="w-full text-center sm:basis-full">
                <EmailSignUpLink />
              </div>
            </div>
          </div>
          {/* The four features, one at a time: hero-features.tsx. */}
          <div
            className="hero-rise mx-auto mt-12 max-w-6xl px-3 sm:mt-16 sm:px-6 lg:px-8"
            style={{ "--rd": ".55s" } as CSSProperties}
          >
            <HeroFeatures />
          </div>
        </div>
      </section>

      {/* Real employers, drifting: logo-strip.tsx. */}
      <LogoStrip />

      {/* Why it matters, played in a framed box: statement.tsx. */}
      <Statement />

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
                eyebrow="FAQ"
                title="Questions, answered."
              />
            </FocusIn>
          </div>
          <FocusIn>
            <FaqList items={faqs} className="faq-rise mt-12 lg:mt-0 lg:max-w-none" />
          </FocusIn>
        </div>
      </section>

      {/* The closing call to action, as every feature page has, on the
          brand's colour, over the row of status chips. */}
      <ClosingCta
        title={closing.title}
        subtitle={closing.subtitle}
        chips={closing.chips}
        background={backdrop({
          tint: "var(--color-brand-tint)",
          glow: "var(--color-brand)",
        })}
      />
    </main>
  );
}
