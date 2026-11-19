import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { cn } from "@/lib/cn";

import { PrimaryButton, SecondaryButton } from "../buttons";
import { site } from "../data";
import { backdrop } from "../features/catalog";
import { FeatureIcon } from "../features/feature-icon";
import { CONTAINER, HERO_PILL, PANEL, PANEL_INSET, TYPE } from "../layout-parts";
import type { Resource } from "./catalog";

/** The brand violet over its tint, like the Pricing page's panels. */
const GROUND = backdrop({
  tint: "var(--color-brand-tint)",
  glow: "var(--color-landing-brand-400)",
});

/** A placeholder's title and description. It stays out of search results
 *  until the real page replaces it. */
export function comingSoonMetadata(resource: Resource): Metadata {
  return {
    title: resource.name,
    description: resource.soon?.summary ?? resource.line,
    robots: { index: false },
  };
}

/**
 * The page a Resources item shows while it has none of its own: its name,
 * a plain "Coming soon", what the page will hold (the item's `soon` copy in
 * catalog.ts), a page that exists now, and the sign-up. It promises nothing
 * that is not built.
 */
export function ComingSoonPage({ resource }: { resource: Resource }) {
  const { soon } = resource;
  if (!soon) notFound();

  return (
    <main id="main" className="flex-1">
      <section className={cn(PANEL_INSET, "mb-2 sm:mb-6")}>
        <div className={cn(PANEL, "py-20 sm:py-28 lg:py-32")} style={{ background: GROUND }}>
          <div className={cn(CONTAINER, "text-center")}>
            <p className={cn(HERO_PILL, "py-1 pl-1")}>
              <FeatureIcon feature={resource} className="rounded-full" />
              {resource.name}
            </p>
            <h1 className={cn(TYPE.display, "text-ink mx-auto mt-6 max-w-4xl")}>Coming soon.</h1>
            <p className="text-ink-muted mx-auto mt-5 max-w-2xl text-lg leading-[1.55] text-pretty">
              {soon.summary}
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <PrimaryButton href={site.primaryCta.href} size="lg">
                {site.primaryCta.label}
              </PrimaryButton>
              <SecondaryButton href={soon.meanwhile.href} size="lg">
                {soon.meanwhile.label}
              </SecondaryButton>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
