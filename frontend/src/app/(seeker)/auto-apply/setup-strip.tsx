"use client";

import { useEffect, useState } from "react";

import { ChromeIcon } from "@/components/icons";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EXTENSION_INSTALL_URL, extensionState } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

/**
 * Auto Apply's setup banner (KAN-424): shown only while the Chrome
 * extension is missing, the one thing Auto Apply can't run without. The
 * extension is asked itself (`ping`) on load and when the student comes
 * back to the tab, since an install happens elsewhere. Before it answers it
 * counts as installed, so a student who has it never sees the banner flash
 * in.
 *
 * ONLY WHAT IS REQUIRED (asked for 2026-10-29). It was "Set Up Auto Apply,
 * 1 of 3 done" with a Configure dialog, counting a default resume and the
 * Claude MCP as steps too, and students read all three as required. Both
 * are optional, so each now shows where it helps instead: a row with no
 * resume says No Resume and its Resume cell picks one, and while
 * questions wait Up Next's Write N Questions links to Written Answers,
 * which offers Connect Claude while their Claude isn't connected
 * (./write-with-claude.tsx).
 *
 * ADD TO CHROME opens the extension's Chrome Web Store page
 * (`EXTENSION_INSTALL_URL`), from the button or anywhere on the card. It had
 * no link while `NEXT_PUBLIC_EXTENSION_INSTALL_URL` was unset, and said its
 * link was coming soon though the Store page is public (2026-11-10).
 *
 * IT OPENS, IT DOES NOT POP IN (2026-11-10). The answer comes after the
 * page has drawn, so for a student without the extension the banner
 * pushed Up Next down in one jump. Its row now grows from nothing
 * (`grid-rows` 0fr to 1fr, 300ms), so the table glides down to make room;
 * with reduced motion it simply appears. The gap under it is its own
 * (`mb-8`, inside the row, so it closes with it), and the page drops Up
 * Next's top margin after it (../auto-apply-panel.tsx).
 */
export function SetupStrip() {
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

  const missing = installed === false;

  return (
    <div
      data-setup-strip
      aria-hidden={!missing}
      inert={!missing}
      className={cn(
        "ease-glide grid transition-[grid-template-rows] duration-300 motion-reduce:transition-none",
        missing ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
      )}
    >
      <div className="min-h-0 overflow-hidden">
        {/* The whole card is the way to the Store, its edge darkening
            under the pointer: it read as a card that should do something
            and did nothing. The click layer is hidden from a keyboard and
            a screen reader, which reach the button. */}
        <Card className="hover:border-ink-meta relative mb-8 flex flex-col gap-4 transition-colors duration-150 @2xl/main:flex-row @2xl/main:items-center">
          <a
            href={EXTENSION_INSTALL_URL}
            target="_blank"
            rel="noreferrer"
            tabIndex={-1}
            aria-hidden="true"
            className="rounded-card absolute inset-0 z-1"
          />
          <span className="border-border-subtle bg-panel rounded-control flex size-10 shrink-0 items-center justify-center border">
            <ChromeIcon className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-label text-ink font-semibold">Add the Chrome Extension</h2>
            <p className="text-note text-ink-meta mt-0.5">
              Auto Apply fills each application in your own Chrome, and you press Submit.
            </p>
          </div>
          <ButtonLink
            href={EXTENSION_INSTALL_URL}
            target="_blank"
            rel="noreferrer"
            size="sm"
            className="z-2"
          >
            <ChromeIcon className="size-4" />
            Add to Chrome
            <span className="sr-only"> (opens the Chrome Web Store in a new tab)</span>
          </ButtonLink>
        </Card>
      </div>
    </div>
  );
}
