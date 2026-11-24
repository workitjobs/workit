import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { RangeSwitch } from "./range-switch";

/**
 * Home's frame: the page's width and gutters, the range switch, the numbers'
 * grid, then Top Matches and Activity. The greeting is in the top bar
 * (../layout.tsx). The page (./page.tsx) fills it with what it read and
 * ./loading.tsx with skeletons, so the two are one layout by construction:
 * the loading state is replaced by the page without a pixel moving, which
 * two copies of this markup would not keep for long.
 *
 * Every seeker page's spacing (KAN-821): 24px under the bar (`py-6`) and
 * 24px between groups (`gap-6`), set here once, so a card passes no margin
 * of its own. Home was 20px under the bar, 20px to the numbers and 16px
 * between cards, so the page jumped against the others in the sidebar.
 */
export function HomeFrame({
  tiles,
  topMatches,
  activity,
}: {
  /** The four numbers, each a cell of the grid. */
  tiles: ReactNode;
  topMatches: ReactNode;
  activity: ReactNode;
}) {
  return (
    <div
      className={cn(
        "max-w-dashboard mx-auto flex w-full flex-1 flex-col gap-6 py-6",
        SEEKER_GUTTER,
      )}
    >
      <header className="flex justify-end">
        {/* Find Jobs sat beside it until KAN-261: the sidebar's Jobs row and
            the Excellent Matches tile already lead there. */}
        <RangeSwitch />
      </header>

      {/* The numbers, in a grid of their own: four across, with Activity
          the full width under them. */}
      <div className="grid grid-cols-2 gap-4 @4xl/main:grid-cols-4">{tiles}</div>

      {topMatches}
      {activity}
    </div>
  );
}
