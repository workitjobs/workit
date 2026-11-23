import { cn } from "@/lib/cn";

import type { Feature } from "./catalog";

const SIZES = {
  sm: { box: "size-6", tile: "size-6 rounded-md", icon: "size-3.5" },
  md: { box: "size-9", tile: "size-9 rounded-lg", icon: "size-[18px]" },
};

/**
 * A feature's mark. A feature with its own (`mark`, feature-marks.tsx: a
 * piece of its screen on a squircle, KAN-923) draws that; anything else
 * draws its icon on a tile in its own colour, the `onGlow` pair. The home
 * page's feature chips and journey steps, the Features menu, each feature
 * page's hero pill and the related-feature cards all draw it, so a feature
 * wears one mark site-wide. The Resources menu draws its items as tiles,
 * on one neutral colour (resources/catalog.ts). An item with no `onGlow`
 * draws white on its `glow`, which must then hold 4.5:1 (the resources'
 * grey does).
 */
export function FeatureIcon({
  feature,
  size = "sm",
  className,
}: {
  feature: Pick<Feature, "icon" | "glow"> & Partial<Pick<Feature, "onGlow" | "mark">>;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const { icon: Icon, mark: Mark, glow, onGlow = { fill: glow, ink: "white" } } = feature;
  if (Mark) return <Mark className={cn("shrink-0", SIZES[size].box, className)} />;
  return (
    <span
      aria-hidden="true"
      className={cn("flex shrink-0 items-center justify-center", SIZES[size].tile, className)}
      style={{ background: onGlow.fill, color: onGlow.ink }}
    >
      <Icon aria-hidden className={SIZES[size].icon} />
    </span>
  );
}
