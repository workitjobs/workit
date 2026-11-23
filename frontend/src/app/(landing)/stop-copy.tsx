import Link from "next/link";

import { cn } from "@/lib/cn";

import { features, type FeatureId } from "./feature-data";
import { FEATURES } from "./features/catalog";
import { FeatureIcon } from "./features/feature-icon";
import { SoonChip, TYPE } from "./layout-parts";
import { tourTab } from "./tour-tabs";

/**
 * A feature's copy beside its animation: its chip (mark, label and, for a
 * step not built yet, "Coming soon"), its heading, its line and one link
 * to its feature page. The home hero's feature card draws it (KAN-923);
 * the pinned product tour, unmounted, drew it per stop. Copy is
 * `features` in feature-data.ts.
 */
export function StopCopy({ id, className }: { id: FeatureId; className?: string }) {
  const feature = features.find((item) => item.id === id) ?? features[0];
  const { label, page } = tourTab(id);
  const { href, name } = FEATURES[page];
  return (
    <div className={className}>
      <p className="text-ink inline-flex items-center gap-2 text-sm font-medium">
        <FeatureIcon feature={FEATURES[page]} />
        {label}
        {feature.soon && <SoonChip />}
      </p>
      <h2 className={cn(TYPE.card, "text-ink mt-4")}>{feature.title}</h2>
      <p className="text-ink-meta mt-3 text-pretty">{feature.description}</p>
      {/* One link per feature, to its page. A "Try it free" beside it made
          two calls to action for one paragraph; the hero's buttons already
          ask for the sign-up. */}
      <div className="mt-6 text-sm font-medium">
        {/* The ::after widens what a tap reaches to about 48px, with the
            underlined link drawn as before: alone it was 23px tall. */}
        <Link
          href={href}
          className="group text-ink relative inline-flex items-center gap-1.5 border-b border-current pb-0.5 after:absolute after:-inset-3 after:content-['']"
        >
          Learn more<span className="sr-only"> about {name}</span>
          <span
            aria-hidden="true"
            className="transition-transform duration-200 group-hover:translate-x-0.5"
          >
            →
          </span>
        </Link>
      </div>
    </div>
  );
}
