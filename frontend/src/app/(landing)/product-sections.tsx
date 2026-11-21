import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { Arrive } from "./arrive";

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
              <Arrive>
                {/* The label and the headline rise as the section arrives
                    (`.rise`), the label first. The feature's label, its 36px mark and its name at 18px:
                    at 24px and 14px it read as a caption over the 48px
                    serif (the user's catch). */}
                <p className="rise text-ink inline-flex items-center gap-3 text-lg font-medium">
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
                  className={cn(TYPE.product, "rise text-ink mt-4 max-w-[12em] text-balance")}
                  style={{ "--rise": "0.1s" } as CSSProperties}
                >
                  {content.hero.title}
                </h2>
              </Arrive>
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
