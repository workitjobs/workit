"use client";

import { DesktopIcon, XIcon } from "@phosphor-icons/react/ssr";

import { ButtonLink } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Notice } from "@/components/ui/notice";
import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { DESKTOP_OFFER_KEY } from "@/lib/local-drafts";
import { storedChoice } from "@/lib/stored-choice";
import { useIsMac } from "@/lib/use-mac";

/** Up Next's length from which the offer shows: the app's gain is filling
 *  several forms at once, which one or two queued jobs don't need. */
export const OFFER_FROM = 3;

const [useOffer, setOffer] = storedChoice(DESKTOP_OFFER_KEY, ["open", "closed"], "open");

/**
 * Up Next's offer of WorkIt Auto Apply, the Mac app (KAN-922): the moment
 * of need, a queue long enough to fill several at once. It shows only
 * while there is a build to download (lib/auto-apply-desktop.ts), on a Mac
 * (lib/use-mac.ts), with OFFER_FROM jobs or more in the queue, until the
 * student closes it; this browser remembers that, and Sign Out forgets it
 * (lib/local-drafts.ts). WorkIt can't tell yet whether the student already
 * has the app, so a student who does closes it once.
 *
 * Get the Mac App opens the signed-in page (../../auto-apply-desktop/),
 * where the download and the steps on WorkIt are. The violet `offer` tone
 * of the queue's notice (components/ui/notice.tsx): nothing waits on the
 * student here, unlike the amber one for written questions.
 */
export function DesktopOffer({ queued }: { queued: number }) {
  const isMac = useIsMac();
  const offer = useOffer();
  if (!DESKTOP_DOWNLOAD_URL || !isMac || offer === "closed" || queued < OFFER_FROM) return null;

  return (
    <Notice
      Icon={DesktopIcon}
      tone="offer"
      className="mt-4"
      actions={
        <>
          <ButtonLink href="/auto-apply-desktop" variant="secondary" size="sm">
            Get the Mac App
          </ButtonLink>
          <IconButton
            place="row"
            tooltip={false}
            label="Dismiss"
            onClick={() => setOffer("closed")}
          >
            <XIcon aria-hidden />
          </IconButton>
        </>
      }
    >
      {queued} jobs in your queue. WorkIt Auto Apply for Mac fills several at once in the
      background, and you press Submit on each.
    </Notice>
  );
}
