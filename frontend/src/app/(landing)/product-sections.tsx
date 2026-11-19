import Link from "next/link";

import { cn } from "@/lib/cn";

import { FEATURES, type FeatureSlug } from "./features/catalog";
import { featureContent } from "./features/content";
import { FeatureIcon } from "./features/feature-icon";
import { CONTAINER, studioGround, TYPE } from "./layout-parts";
import { ProductAccordion } from "./product-accordion";

/** The products the home page goes deep on, in the pipeline's order. The
 *  tracker and Scout have their pages; the journey above covers tracking. */
const PRODUCTS: FeatureSlug[] = ["resumes", "matching", "auto-apply"];

/** A second colour for each box's ground, so no box is one flat hue. */
const ACCENTS: Partial<Record<FeatureSlug, string>> = {
  resumes: "var(--color-brand)",
  matching: "var(--color-advanced)",
  "auto-apply": "var(--color-advanced)",
};

/**
 * One section per product (KAN-923), after Calendly's: the feature's chip,
 * its page's headline in the serif (`TYPE.product`), a link to its page,
 * then its page's deep dives as rows beside a square framed box
 * (`ProductAccordion`). The copy and the still scenes are the feature
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
          <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
            <div className="max-w-2xl">
              <p className="text-ink inline-flex items-center gap-2 text-sm font-medium">
                <FeatureIcon feature={page} />
                {page.name}
              </p>
              <h2 id={titleId} className={cn(TYPE.product, "text-ink mt-4")}>
                {content.hero.title}
              </h2>
            </div>
            <Link
              href={page.href}
              className="group text-ink relative mb-1 inline-flex items-center gap-1.5 border-b border-current pb-0.5 text-sm font-medium after:absolute after:-inset-3 after:content-['']"
            >
              Explore {page.name}
              <span
                aria-hidden="true"
                className="transition-transform duration-200 group-hover:translate-x-0.5"
              >
                →
              </span>
            </Link>
          </div>
          <ProductAccordion
            items={content.sections.map((section) => ({
              title: section.title,
              body: section.body,
              visual: <section.visual />,
            }))}
            ground={studioGround({ tint: page.tint, glow: page.glow, accent: ACCENTS[slug] })}
            accent={page.glow}
            flip={i % 2 === 1}
          />
        </div>
      </section>
    );
  });
}
