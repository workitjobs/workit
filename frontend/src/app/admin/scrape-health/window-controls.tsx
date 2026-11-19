import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import { SegmentedLinks } from "@/components/ui/segmented-control";
import { moved, SPANS, type Window, windowHref } from "@/lib/scrape-status";

const ARROW =
  "border-border-surface bg-panel text-ink inline-flex size-8 items-center justify-center rounded-full border";

/** An arrow that moves the window, or its faded shape where the window cannot move. */
function Arrow({ to, label, children }: { to: Window | null; label: string; children: ReactNode }) {
  if (!to) {
    return (
      <span aria-disabled className={`${ARROW} text-ink-subtle`} title={label}>
        {children}
      </span>
    );
  }
  return (
    <Link
      href={windowHref(to)}
      aria-label={label}
      title={label}
      className={`${ARROW} hover:bg-hover focus-visible:ring-brand-ring focus-visible:ring-2 focus-visible:outline-none`}
    >
      {children}
    </Link>
  );
}

/**
 * The page's one set of time controls (KAN-879): the period (how many days
 * the whole page shows), and two arrows that move that window older or
 * newer by a week or a month, as Move By says. All are links, so the
 * address holds the window: a reload, Back and a shared link keep it. The
 * tiles, the chart and the table all read the same window. The chart had
 * its own zoom and arrows beside the page's day pills; a design review
 * found two time controls on one page.
 */
export function WindowControls({ window }: { window: Window }) {
  const unit = window.step === "week" ? "Week" : "Month";
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5">
        <Arrow to={moved(window, -1)} label={`Back One ${unit}`}>
          <CaretLeftIcon size={16} aria-hidden />
        </Arrow>
        <SegmentedLinks
          label="Move By"
          value={window.step}
          options={[
            { value: "week", label: "Week", href: windowHref({ ...window, step: "week" }) },
            { value: "month", label: "Month", href: windowHref({ ...window, step: "month" }) },
          ]}
        />
        <Arrow to={moved(window, 1)} label={`Forward One ${unit}`}>
          <CaretRightIcon size={16} aria-hidden />
        </Arrow>
      </div>
      <SegmentedLinks
        label="Period"
        value={String(window.days)}
        options={SPANS.map((days) => ({
          value: String(days),
          label: `${days} Days`,
          // A longer period may not fit as far back: windowOf cuts `back` on arrival.
          href: windowHref({ ...window, days }),
        }))}
      />
    </div>
  );
}
