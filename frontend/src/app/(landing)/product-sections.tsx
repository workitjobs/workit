import { ArrowDownIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

import { featuresIntro } from "./data";
import { deepDiveAnchor, FEATURES, type FeatureSlug } from "./features/catalog";
import { featureContent } from "./features/content";
import { FeatureIcon } from "./features/feature-icon";
import { CONTAINER, studioGround, TYPE } from "./layout-parts";
import { ProductAccordion } from "./product-accordion";
import { ToolsCollapse } from "./tools-collapse";

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
 * a flat tile in its feature's pale tint (`TILE`), its mark ringed in white
 * so it stands off the tint, then its name, its selling line
 * (`featuresIntro.products`) and "See how", with no picture, since the
 * picture is a scroll away. Grey, the four read as alike (the user's call,
 * 2026-11-20); flat, never a fade to white, which read as AI-made. The
 * line was "Fixes" and the problem above it answered, which named the
 * problem but not what the product does (the user's catch, 2026-11-20).
 * From lg up the row arrives as the tools it replaces collapse into it,
 * while the section, its heading (`heading`) included, pins
 * (`ToolsCollapse`): each tile (`data-tile`) starts as its empty slot
 * (`data-ghost`) and its body (`data-tile-body`) fills it as its tools
 * land.
 */
/** A tile's fill: its feature's colour mixed into white, the same share for
 *  all four so none stands out, a step deeper on hover. */
const TILE = (glow: string, amount: number) => `color-mix(in oklab, ${glow} ${amount}%, white)`;

export function FeatureJumps({ heading }: { heading: ReactNode }) {
  return (
    <ToolsCollapse heading={heading}>
      <ul className="relative grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {PRODUCTS.map((slug) => {
          const page = FEATURES[slug];
          return (
            <li key={slug} data-tile className="relative">
              {/* The product's empty slot while the tools lie scattered
                (`ToolsCollapse`): a dashed outline in its colour with its
                mark and name, which the tile fills as its tools land. Shown
                only from lg up with motion (landing.css). */}
              <span aria-hidden="true" data-ghost style={{ "--ghost": page.glow } as CSSProperties}>
                <FeatureIcon feature={page} size="md" />
                <span className={cn(TYPE.item, "text-ink-meta")}>{page.name}</span>
              </span>
              {/* A `Link` to "/#slug", as the Features menu's "/#hiring-systems"
                is: as a plain anchor, "#slug" or "/#slug" jumped to the
                page's top instead of to the section. */}
              <Link
                href={`/#${slug}`}
                data-tile-body
                className="group focus-visible:outline-ink relative flex h-full flex-col rounded-2xl bg-(--tile) p-5 transition-colors hover:bg-(--tile-hover) focus-visible:outline-2 focus-visible:outline-offset-2"
                style={
                  {
                    "--tile": TILE(page.glow, 9),
                    "--tile-hover": TILE(page.glow, 14),
                  } as CSSProperties
                }
              >
                {/* A white ring and a slate shadow lift the mark's pastel
                  squircle off a tint of its own colour, where it blended. */}
                <span className="self-start rounded-[13px] shadow-[0_0_0_2.5px_white,0_6px_12px_-6px_rgb(15_23_42/0.35)]">
                  <FeatureIcon feature={page} size="md" className="block" />
                </span>
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
    </ToolsCollapse>
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
