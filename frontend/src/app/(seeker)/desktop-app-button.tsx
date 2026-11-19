"use client";

import { DownloadSimpleIcon } from "@phosphor-icons/react/ssr";

import { ButtonLink } from "@/components/ui/button";
import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { useIsMac } from "@/lib/use-mac";

/**
 * The top bar's way to WorkIt Auto Apply, the Mac app (KAN-922), on every
 * seeker page: the app's counterpart of the public header's Download link,
 * as claude.ai and chatgpt.com keep theirs in sight. It opens the signed-in
 * page (./auto-apply-desktop/), with the download and the steps on WorkIt.
 * It shows only while there is a build to download
 * (lib/auto-apply-desktop.ts) and on a Mac (lib/use-mac.ts), and from sm,
 * since a phone's bar has no room and can't run the app.
 */
export function DesktopAppButton() {
  const isMac = useIsMac();
  if (!DESKTOP_DOWNLOAD_URL || !isMac) return null;
  return (
    <ButtonLink href="/auto-apply-desktop" variant="secondary" size="sm" className="max-sm:hidden">
      <DownloadSimpleIcon aria-hidden />
      Download App
    </ButtonLink>
  );
}
