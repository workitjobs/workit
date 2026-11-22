import { FileTextIcon, KanbanIcon, TargetIcon } from "@phosphor-icons/react/ssr";
import { LightningRoundedIcon } from "@/components/custom-icons";
import type { ComponentType } from "react";

import { SparkleIcon } from "@/components/sparkle-icon";

import { FEATURE_MARKS } from "./feature-marks";

/**
 * The five feature pages, in the Features menu's order: each page's slug,
 * name, icon and colour. The header's Features menu, the footer, each page's
 * related-feature cards and the home tour's "Learn more" links all read
 * this list, so a page added or renamed here moves everywhere at once.
 * Each page's copy lives in its own file under `content/`, never here.
 *
 * The colours are the home tour's (product-tour.tsx reads them from here):
 * the advanced blue for resumes, peach for matching (violet until
 * 2026-11-21: violet is the brand's, so no product wears it), positive
 * green for auto apply, the match pink on the danger tint for the tracker (the
 * tour's Updates stop). Scout had no stop, so it takes amber, the one app
 * colour the others leave free. A mark sits on `onGlow`, never on `glow`.
 */
export type FeatureSlug = "resumes" | "matching" | "auto-apply" | "tracker" | "scout";

export type Feature = {
  slug: FeatureSlug;
  name: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  /** Its own mark, a piece of its screen on a squircle (feature-marks.tsx),
   *  which `FeatureIcon` draws in place of the icon on a tile. Scout, off
   *  the site, has none. */
  mark?: ComponentType<{ className?: string }>;
  /** The soft ground behind the feature's visuals. */
  tint: string;
  /** The feature's own colour: the ground's blobs only. */
  glow: string;
  /** Its marks (the icon tile, a step's number, a check): a fill and the
   *  glyph on it, a pair that holds 4.5:1. White on `glow` fell to 2.8:1 on
   *  the green and 3.19:1 on the amber (KAN-580), so green fills with
   *  `positive-ink` and amber takes ink, not white. */
  onGlow: { fill: string; ink: string };
};

function feature(slug: FeatureSlug, rest: Omit<Feature, "slug" | "href">): Feature {
  return { slug, href: `/features/${slug}`, ...rest };
}

export const FEATURES: Record<FeatureSlug, Feature> = {
  resumes: feature("resumes", {
    name: "Resume Builder",
    icon: FileTextIcon,
    mark: FEATURE_MARKS.resumes,
    tint: "var(--color-advanced-tint)",
    glow: "var(--color-advanced)",
    onGlow: { fill: "var(--color-advanced)", ink: "white" },
  }),
  matching: feature("matching", {
    name: "Job Matching",
    icon: TargetIcon,
    mark: FEATURE_MARKS.matching,
    tint: "var(--color-matching-tint)",
    glow: "var(--color-matching)",
    onGlow: { fill: "var(--color-matching-ink)", ink: "white" },
  }),
  "auto-apply": feature("auto-apply", {
    name: "Auto Apply",
    // The app's own Auto Apply glyph (the sidebar, the Jobs page's filters).
    icon: LightningRoundedIcon,
    mark: FEATURE_MARKS["auto-apply"],
    tint: "var(--color-positive-tint)",
    glow: "var(--color-positive)",
    onGlow: { fill: "var(--color-positive-ink)", ink: "white" },
  }),
  tracker: feature("tracker", {
    name: "Application Tracker",
    // The sidebar's Applications glyph.
    icon: KanbanIcon,
    mark: FEATURE_MARKS.tracker,
    tint: "var(--color-danger-tint)",
    glow: "var(--color-updates)",
    onGlow: { fill: "var(--color-updates)", ink: "white" },
  }),
  scout: feature("scout", {
    name: "Scout",
    // The one mark for Scout and AI (frontend/CLAUDE.md).
    icon: SparkleIcon,
    tint: "var(--color-warning-tint)",
    glow: "var(--color-warning-strong)",
    onGlow: { fill: "var(--color-warning-strong)", ink: "var(--color-ink)" },
  }),
};

/**
 * Features the site does not show while they do not work in the app. Scout
 * is off there (Ask Scout and Fill With Scout are hidden), so the user had it
 * taken off the site on 2026-11-19 (KAN-923): no menu item, footer link,
 * related card or pricing row, and `/features/scout` is a 404. Its content
 * file and animations stay, unmounted; delete its slug here to bring it back.
 */
const HIDDEN: FeatureSlug[] = ["scout"];

/** The pages the site shows, in menu order. */
export const featurePages = Object.values(FEATURES).filter((page) => !HIDDEN.includes(page.slug));

export function isFeatureSlug(slug: string): slug is FeatureSlug {
  return featurePages.some((page) => page.slug === slug);
}

/** A feature's soft, two-blob gradient over its tint: the home tour's
 *  backdrop, behind every visual of that feature. */
export function backdrop({ tint, glow }: Pick<Feature, "tint" | "glow">) {
  const blob = (amount: number) => `color-mix(in oklab, ${glow} ${amount}%, transparent)`;
  return `radial-gradient(55% 65% at 12% 18%, ${blob(38)}, transparent), radial-gradient(50% 60% at 88% 85%, ${blob(30)}, transparent), radial-gradient(40% 50% at 70% 10%, white, transparent), ${tint}`;
}

/**
 * A feature page deep dive's anchor, from its title: "Tailored to each job
 * posting" is `#tailored-to-each-job-posting`. The feature page sets it on
 * the deep dive (feature-page.tsx) and the home page's product rows link to
 * it (product-accordion.tsx), so both read this one function.
 */
export function deepDiveAnchor(title: string) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
