"use client";

import { GoogleChromeLogoIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useState } from "react";

import { buttonClasses } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { EXTENSION_INSTALL_URL, extensionState } from "@/lib/autofill-extension";

/**
 * The one thing Auto Apply can't run without, the Chrome extension, as the
 * shared notice (components/ui/notice.tsx) at the top of the queue, only
 * while it is missing (2026-11-23). An added extension says nothing: a
 * status that is fine needs no place on the page.
 *
 * It was the first of the setup row's three cells from 2026-11-10, where
 * "Add to Chrome" was the smallest text on the page and an added
 * extension kept a dead tile for good; before that, a card that showed
 * only while the extension was missing, which this is again.
 *
 * THE EXTENSION is asked itself (`ping`) on load and when the student comes
 * back to the tab, since an install happens elsewhere. Until it answers,
 * nothing shows, so the notice never flashes for a student who has it.
 * Add to Chrome opens its Chrome Web Store page (`EXTENSION_INSTALL_URL`)
 * in a new tab: bordered, the notice's button for an action that goes
 * somewhere new (frontend/docs/design.md).
 */
export function ExtensionNotice({ className }: { className?: string }) {
  const installed = useExtensionInstalled();
  if (installed !== false) return null;
  return (
    <Notice
      Icon={GoogleChromeLogoIcon}
      className={className}
      actions={
        <a
          href={EXTENSION_INSTALL_URL}
          target="_blank"
          rel="noreferrer"
          className={buttonClasses({ variant: "secondary", size: "sm" })}
        >
          Add to Chrome
          <span className="sr-only"> (opens the Chrome Web Store in a new tab)</span>
        </a>
      }
    >
      Auto Apply fills out your applications with the WorkIt extension for Chrome. Add it to start.
    </Notice>
  );
}

/** Whether the extension is in this Chrome: null until it answers. */
function useExtensionInstalled() {
  const [installed, setInstalled] = useState<boolean | null>(null);
  useEffect(() => {
    let stopped = false;
    const ask = async () => {
      const state = await extensionState();
      if (!stopped) setInstalled(state.installed);
    };
    void ask();
    window.addEventListener("focus", ask);
    return () => {
      stopped = true;
      window.removeEventListener("focus", ask);
    };
  }, []);
  return installed;
}
