import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import { SegmentedLinks } from "@/components/ui/segmented-control";
import {
  datesOf,
  moved,
  rangeOf,
  resized,
  SPANS,
  type Window,
  windowHref,
} from "@/lib/scrape-status";

const ARROW =
  "border-border-surface bg-panel inline-flex size-8 shrink-0 items-center justify-center rounded-full border";

/**
 * An arrow that moves the window one period, named by the days it shows
 * ("Show Oct 26 to Nov 8"), so its name is true where the last step is a
 * short one. Where the window cannot move, its faded shape, named as off.
 * No tooltip: a Previous or Next arrow is read on sight (`ui/tip.tsx`), and
 * the days between the two arrows say what they move.
 */
function Arrow({
  to,
  href,
  today,
  off,
  children,
}: {
  to: Window | null;
  /** The page's address for `to`. */
  href: (window: Window) => string;
  today: string;
  /** The arrow's name where the window cannot move: "No Earlier Days". */
  off: string;
  children: ReactNode;
}) {
  if (!to) {
    return (
      <a role="link" aria-disabled="true" aria-label={off} className={`${ARROW} text-ink-subtle`}>
        {children}
      </a>
    );
  }
  return (
    <Link
      href={href(to)}
      aria-label={`Show ${rangeOf(datesOf(to, today))}`}
      className={`${ARROW} text-ink hover:bg-hover focus-visible:ring-brand-ring focus-visible:ring-2 focus-visible:outline-none`}
    >
      {children}
    </Link>
  );
}

/**
 * The page's one time control (KAN-879): the period, which is how many days
 * the whole page shows, and two arrows that move those days one period
 * earlier or later, around the days in view ("Nov 9 to Nov 22"). All are
 * links, so the address holds the window: a reload, Back and a shared link
 * keep it. The tiles, the chart and the table all read the same window.
 *
 * ONE VOCABULARY, DAYS. The arrows had a switch of their own between them,
 * Move By (Week or Month), beside the periods (7, 14, 30 and 90 Days): two
 * rows of lengths of time in two sets of words, and the user could not tell
 * what each did (2026-11-22). The period is now also the step, so 7 Days
 * moves week by week and 30 Days month by month, and the days in view sit
 * where that switch was. Before that the chart had its own zoom and arrows
 * beside the page's day pills, which a design review found was two time
 * controls on one page.
 *
 * Fill Health uses it too, with its own `path` and the filters its address
 * keeps (`keep`), so every admin page moves through time the same way.
 */
export function WindowControls({
  window,
  today,
  path,
  keep,
}: {
  window: Window;
  /** The newest day, YYYY-MM-DD (UTC): the day the API's answer was read. */
  today: string;
  /** The admin page these links open; Scrape Health when left out. */
  path?: string;
  /** The page's other filters, kept in every link. */
  keep?: Record<string, string>;
}) {
  const href = (to: Window) => windowHref(to, path, keep);
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5">
        <Arrow to={moved(window, -1)} href={href} today={today} off="No Earlier Days">
          <CaretLeftIcon size={16} aria-hidden />
        </Arrow>
        {/* A fixed room for the longest range, so the arrows hold still as the days change. */}
        <p className="text-label text-ink min-w-36 text-center tabular-nums" aria-live="polite">
          {rangeOf(datesOf(window, today))}
        </p>
        <Arrow to={moved(window, 1)} href={href} today={today} off="No Later Days">
          <CaretRightIcon size={16} aria-hidden />
        </Arrow>
      </div>
      <SegmentedLinks
        label="Period"
        value={String(window.days)}
        options={SPANS.map((days) => ({
          value: String(days),
          label: `${days} Days`,
          href: href(resized(window, days)),
        }))}
      />
    </div>
  );
}
