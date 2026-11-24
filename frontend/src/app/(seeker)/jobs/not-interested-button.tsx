import { ProhibitIcon } from "@phosphor-icons/react/ssr";

import { IconButton } from "@/components/ui/icon-button";

/** Whether Not Interested works. Off (2026-11-09): nothing stores the choice
 *  yet, so the button is not drawn at all. It stood faded in every card's
 *  action row as "Coming Soon" (`soon`, KAN-569), a dead button to look past,
 *  as Ask Scout was (`ASK_SCOUT_LIVE`). Set it to true once the choice is
 *  stored. */
export const NOT_INTERESTED_LIVE = false;

/** Not Interested, on the large card (36px and round, as Save is beside it)
 *  and, `quiet`, on the compact card as a bare glyph. Drawn only while
 *  NOT_INTERESTED_LIVE is on. */
export function NotInterestedButton({ title, quiet = false }: { title: string; quiet?: boolean }) {
  if (!NOT_INTERESTED_LIVE) return null;
  return (
    <IconButton
      label={`Not Interested in ${title}`}
      tooltip="Not Interested"
      variant={quiet ? "glyph" : "soft"}
      className={quiet ? undefined : "size-9"}
    >
      <ProhibitIcon aria-hidden className="size-4" />
    </IconButton>
  );
}
