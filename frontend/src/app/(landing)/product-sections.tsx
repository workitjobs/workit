import { ArrowDownIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { cn } from "@/lib/cn";

import { featuresIntro } from "./data";
import { deepDiveAnchor, FEATURES, type FeatureSlug } from "./features/catalog";
import { featureContent } from "./features/content";
import { FeatureIcon } from "./features/feature-icon";
import { CONTAINER, studioGround, TYPE } from "./layout-parts";
import { ProductAccordion } from "./product-accordion";

/** The products the home page goes deep on, in the pipeline's order, each
 *  with four rows (its feature page's four deep dives). The tracker joined
 *  them at the user's ask, in place of the hiring systems, which looked like
 *  a fifth product here and became a chapter of their own (hiring-grid.tsx). */
const PRODUCTS = [
  "resumes",
  "matching",
  "auto-apply",
  "tracker",
] as const satisfies readonly FeatureSlug[];

/**
 * The four products as a row of links, each to its section below (`/#<slug>`,
 * the section's id): the intro under "One app for every step of applying"
 * (page.tsx, `featuresIntro`). It replaced a tabs row over a large card that told the
 * four products' stories, which the product sections then told again, word
 * for word, right below (the web review's first finding, 2026-11-20). Each is
 * a flat grey tile, as the problems' closed cards are: the product's mark, its
 * name, its selling line (`featuresIntro.products`) and "See how", with no
 * picture, since the picture is a scroll away. The line was "Fixes" and the
 * problem above it answered, which named the problem but not what the
 * product does (the user's catch, 2026-11-20).
 */
export function FeatureJumps() {
  return (
    <ul className="mt-10 grid gap-3 sm:grid-cols-2 lg:mt-12 lg:grid-cols-4">
      {PRODUCTS.map((slug) => {
        const page = FEATURES[slug];
        return (
          <li key={slug}>
            {/* A `Link` to "/#slug", as the Features menu's "/#hiring-systems"
                is: as a plain anchor, "#slug" or "/#slug" jumped to the
                page's top instead of to the section. */}
            <Link
              href={`/#${slug}`}
              className="group focus-visible:outline-ink flex h-full flex-col rounded-2xl bg-slate-900/[0.035] p-5 transition-colors hover:bg-slate-900/[0.06] focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              <FeatureIcon feature={page} size="md" />
              <span className={cn(TYPE.item, "text-ink mt-4")}>{page.name}</span>
              <span className="text-ink-meta mt-1.5 text-[15px] leading-snug text-pretty">
                {featuresIntro.products[slug]}
              </span>
              <span className="text-ink mt-auto inline-flex items-center gap-1 pt-4 text-sm font-medium">
                See how
                <ArrowDownIcon
                  aria-hidden="true"
                  className="size-3.5 transition-transform group-hover:translate-y-0.5"
                />
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * One section per product (KAN-923), after Calendly's: the feature's chip
 * and its page's headline in the serif (`TYPE.product`) over its page's
 * deep dives as rows, each with its icon and its own arrow link to that
 * deep dive, beside a square framed box (`ProductAccordion`: from lg up
 * the section pins at the screen's middle and the scroll opens each row). The copy and the still scenes are the feature
 * page's own (`features/content/`), already checked as product claims, so
 * the two pages never disagree. The box alternates sides.
 */
export function ProductSections() {
  return PRODUCTS.map((slug, i) => {
    const page = FEATURES[slug];
    const content = featureContent[slug];
    const titleId = `product-${slug}`;
    return (
      <section key={slug} id={slug} aria-labelledby={titleId} className="py-16 sm:py-24">
        <div className={CONTAINER}>
          <ProductAccordion
            heading={
              <>
                {/* The feature's label, its 36px mark and its name at 18px:
                    at 24px and 14px it read as a caption over the 48px
                    serif (the user's catch). */}
                <p className="text-ink inline-flex items-center gap-3 text-lg font-medium">
                  <FeatureIcon feature={page} size="md" />
                  {page.name}
                </p>
                {/* Two lines at every width, as every product's headline
                    is written (about 30 to 40 characters): the column holds
                    it to two on a desktop, and 12em does on a tablet, where
                    it spans the page and ran on one. Balanced, so the lines
                    are even. */}
                <h2
                  id={titleId}
                  className={cn(TYPE.product, "text-ink mt-4 max-w-[12em] text-balance")}
                >
                  {content.hero.title}
                </h2>
              </>
            }
            items={content.sections.map((section) => ({
              title: section.title,
              body: section.body,
              icon: <section.icon />,
              href: `${page.href}#${deepDiveAnchor(section.title)}`,
              visual: <section.visual />,
            }))}
            ground={studioGround({ glow: page.glow })}
            accent={page.glow}
            flip={i % 2 === 1}
          />
        </div>
      </section>
    );
  });
}
