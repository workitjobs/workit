import { SegmentedLinks } from "@/components/ui/segmented-control";
import { SPANS, type Window, windowHref } from "@/lib/scrape-status";

/**
 * An admin page's one time control (KAN-879): the period, which is how many
 * days the whole page shows, ending today (UTC). Each period is a link, so
 * the address holds it (`?days=`): a reload, Back and a shared link keep it,
 * and every part of the page shows the same days.
 *
 * ONE SETTING, ONE CONTROL (KAN-953, 2026-11-27). Two arrows stood beside
 * the periods, around the days in view ("Nov 9 to Nov 22"), and moved those
 * days one period earlier or later. They went, on every admin page:
 *
 * - They reached no new day. The pages read 90 days and the longest period
 *   is 90 days, so 90 Days already showed every day an arrow could reach;
 *   the arrows only showed older days at a closer zoom. A day's own numbers
 *   are in its column's tooltip.
 * - The forward arrow was off on every first visit, and both were off at 90
 *   Days: a control that is off in the default view is not needed there.
 * - With them the control was a fixed 520px. It left the title row below a
 *   1223px window and broke into two rows of unequal width on a phone,
 *   where the page's header stood 164px tall.
 * - The days in view were written twice, here and in the chart's header,
 *   which keeps them.
 *
 * Before that the arrows had a switch of their own, Move By (Week or Month),
 * beside the periods: two rows of lengths of time in two sets of words, and
 * the user could not tell what each did (2026-11-22). Before that the chart
 * had its own zoom and arrows beside the page's day pills, which a design
 * review found was two time controls on one page.
 *
 * Below sm the switch takes the page's width, four equal parts, so it lines
 * up with the cards under it. Its options are 44px tall to a touch at every
 * width (`ui/segmented-control.tsx`).
 *
 * Every admin page uses it, with its own `path` and the filters its address
 * keeps (`keep`), so they all move through time the same way.
 */
export function WindowControls({
  window,
  path,
  keep,
}: {
  window: Window;
  /** The admin page these links open; Scrape Health when left out. */
  path?: string;
  /** The page's other filters, kept in every link. */
  keep?: Record<string, string>;
}) {
  return (
    <SegmentedLinks
      label="Period"
      value={String(window.days)}
      className="max-sm:w-full"
      options={SPANS.map((days) => ({
        value: String(days),
        label: `${days} Days`,
        href: windowHref({ days }, path, keep),
      }))}
    />
  );
}
