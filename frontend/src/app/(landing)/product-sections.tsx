import { cn } from "@/lib/cn";

import { deepDiveAnchor, FEATURES, type FeatureSlug } from "./features/catalog";
import { featureContent } from "./features/content";
import { FeatureIcon } from "./features/feature-icon";
import { CONTAINER, studioGround, TYPE } from "./layout-parts";
import { ProductAccordion } from "./product-accordion";

/** The products the home page goes deep on, in the pipeline's order. The
 *  tracker has its page; the journey above covers tracking. */
const PRODUCTS: FeatureSlug[] = ["resumes", "matching", "auto-apply"];

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
      <section key={slug} aria-labelledby={titleId} className="py-16 sm:py-24">
        <div className={CONTAINER}>
          <ProductAccordion
            heading={
              <>
                <p className="text-ink inline-flex items-center gap-2 text-sm font-medium">
                  <FeatureIcon feature={page} />
                  {page.name}
                </p>
                <h2 id={titleId} className={cn(TYPE.product, "text-ink mt-4")}>
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
