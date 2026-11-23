import { DownloadSimpleIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { CSSProperties } from "react";

import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { cn } from "@/lib/cn";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";

import { PrimaryButton, SecondaryButton } from "./buttons";
import { ClosingCta } from "./closing-cta";
import { getStarted, hero, homeDescription, site, testimonial } from "./data";
import { DraftLines } from "./draft-lines";
import { GrowIn } from "./grow-in";
import { CONTAINER, PANEL, PANEL_INSET, studioGround, TYPE } from "./layout-parts";
import { HeroCity } from "./hero-city";
import { LogoStrip } from "./logo-strip";
import { Problems } from "./problems";
import { ProductSections } from "./product-sections";
import { SessionSwap } from "./session-swap";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";
import { Testimonial } from "./testimonial";
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
 * the hero says what WorkIt is, then each section leads into the next:
 * proof the jobs are real (the logo strip), where applications get lost
 * (the problems), why WorkIt exists over the whole pipeline as four cells
 * of the drafting grid, each product in depth, and get started
 * (closing-cta.tsx), which runs into the footer. The FAQ went on 2026-11-19 (the
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
      {/* Hero (redrawn 2026-11-21; its pipeline moved down on 2026-11-23):
          the first screen, on the page's own white ground, in the drafting
          grid's frame, the page's first, so its side lines start the rail
          every section below continues. The headline, its line and the
          sign-up pair are centred. The frame hangs from the header: its top
          edge is the header's foot line (header.tsx draws it), so the
          section has no padding above. It is as tall as its words for now:
          the four pipeline cells under them moved to That's why WorkIt
          exists, beside the product sections they link to (the team's
          call), and the hero waits for a visual of its own. */}
      <section
        data-hero-panel
        className="@container relative flex flex-col pb-10 lg:min-h-[max(45rem,min(calc(100svh-4.75rem),54rem))]"
      >
        {/* The city (hero-city.tsx), clipped at the frame's foot line, 1rem
            above the section's foot, so that line is its ground and the
            buildings rise from behind it. A clip of its own: on the
            section it would cut the rails, which run on below. */}
        <div aria-hidden="true" className="absolute inset-x-0 top-0 bottom-4 overflow-hidden">
          <HeroCity />
        </div>
        <div className={cn(CONTAINER, "flex flex-1 flex-col")}>
          <div className="relative flex flex-1 flex-col">
            <DraftLines gap="1.5rem" first />
            <div className="relative mx-auto w-full max-w-5xl pt-14 text-center sm:pt-20 lg:pt-24">
              {/* One line from lg up, sized by the window's width (4.6vw,
                  48 to 72px: the line is about 15.4em wide, so 71% of the
                  window), so it stays inside the rails. The city's height
                  caps are set for it (city-model.ts, `step`). The
                  text is marked for the city's job cards, which keep clear
                  of it (`data-hero-text`, `data-hero-box`: hero-city.tsx). */}
              <h1
                data-hero-text
                className={cn(
                  TYPE.display,
                  "hero-reveal text-ink lg:text-[clamp(3rem,4.6vw,4.5rem)] lg:whitespace-nowrap",
                )}
                style={{ "--rd": ".15s" } as CSSProperties}
              >
                {hero.title}
              </h1>
              <p
                data-hero-text
                className={cn(TYPE.lead, "hero-reveal text-ink-muted mx-auto mt-5 max-w-2xl")}
                style={{ "--rd": ".3s" } as CSSProperties}
              >
                {hero.subtitle}
              </p>
              {/* The sign-up pair for a visitor, or one Open WorkIt for a
                  signed-in student, as the header does (`SessionSwap`:
                  both are drawn, and landing.css shows one by <html
                  data-signed-in>, so the page stays prerendered). The hero
                  offered "Sign up" to a student the header already greeted
                  with Open WorkIt (2026-11-21). Then Download for Mac
                  (KAN-922) as a `SecondaryButton`, only while there is a
                  build. The row wraps, so a third button needs no other
                  change. */}
              <div
                data-hero-box
                className="hero-reveal mt-7 flex w-full flex-col flex-wrap items-center justify-center gap-3 sm:flex-row"
                style={{ "--rd": ".4s" } as CSSProperties}
              >
                <SessionSwap
                  signedOut={
                    <>
                      <SocialSignUpButton provider="google" />
                      <SocialSignUpButton provider="linkedin_oidc" />
                    </>
                  }
                  signedIn={
                    <PrimaryButton href="/go-home" prefetch={false} size="lg">
                      Open WorkIt
                    </PrimaryButton>
                  }
                />
                {DESKTOP_DOWNLOAD_URL && (
                  <SecondaryButton href={site.download.href}>
                    <DownloadSimpleIcon aria-hidden className="size-5" />
                    Download for Mac
                  </SecondaryButton>
                )}
                <SessionSwap
                  signedOut={
                    <div className="w-full text-center sm:basis-full">
                      <EmailSignUpLink />
                    </div>
                  }
                  signedIn={null}
                />
              </div>
            </div>
            {/* The city's room under the text: it is scaled to the panel's
                width below lg (70% of it on a phone's larger build, 40% from
                sm), and from lg up the section's own height leaves it. */}
            <div
              aria-hidden="true"
              className="h-[70cqw] shrink-0 sm:h-[40cqw] lg:h-auto lg:flex-1"
            />
          </div>
        </div>
      </section>

      {/* Real employers, drifting: logo-strip.tsx. The page's one word on
          where the jobs come from: a hiring-systems section at the foot
          said it again and went (the team's call, 2026-11-23). */}
      <LogoStrip />

      {/* Applying as it is, before how WorkIt works: problems.tsx. It
          follows the logo strip straight on: What is WorkIt stood between
          them and said the hero's line again, so its line became the hero's
          headline (the team's call, 2026-11-23). */}
      <Problems />

      {/* The turn from the problems to the product: the four pipeline cells,
          each a link to its product section just below (why-exists.tsx). */}
      <WhyExists />

      {/* Each product in depth, from its feature page: product-sections.tsx.
          A section of four product tiles under "One app for every step of
          applying" stood before these until 2026-11-21: the hero now shows
          the four products and links each to its section, so the tiles
          said it twice (the user's call). */}
      <ProductSections />

      {/* Get started, the page's last word before the footer
          (closing-cta.tsx), on WorkIt's violet blend. "You stay in control"
          (control.tsx) stood here until the user archived it (2026-11-23):
          its file and copy stay, unmounted. */}
      <div className="mt-8 sm:mt-12">
        <ClosingCta
          title={getStarted.title}
          subtitle={getStarted.subtitle}
          background={studioGround({ glow: "var(--color-brand)" })}
        />
      </div>

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
