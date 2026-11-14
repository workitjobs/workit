"use client";

import { CheckIcon, NotepadIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useState } from "react";

import { ChromeIcon } from "@/components/icons";
import { Card } from "@/components/ui/card";
import { OptionRow } from "@/components/ui/option-row";
import { EXTENSION_INSTALL_URL, extensionState } from "@/lib/autofill-extension";

/**
 * Auto Apply's setup, in one row at the top of the page (2026-11-10): the
 * Chrome extension and Application Info, what every application needs,
 * each with where it stands ("Added") and, where there is something to do,
 * a link. They were a card on top that showed only while the extension was
 * missing and a large Application Info card at the foot. Written Answers
 * sat here for a day and left: it is not setup but work a job asks for, so
 * it shows as a notice over the queue while questions wait (./up-next.tsx,
 * `QuestionsNotice`).
 *
 * NO COUNT OF STEPS. It was "Set Up Auto Apply, 1 of 3 done" with a
 * Configure dialog until 2026-10-29, and students read all three as
 * required. Only the extension is: the other two say what they hold, not
 * that they are undone.
 *
 * THE EXTENSION is asked itself (`ping`) on load and when the student comes
 * back to the tab, since an install happens elsewhere. Until it answers its
 * line says "Checking…". Missing, "Add to Chrome" opens its Chrome Web Store
 * page (`EXTENSION_INSTALL_URL`); added, the cell is not a link.
 */
export function SetupRow() {
  const installed = useExtensionInstalled();
  return (
    <Card
      as="section"
      padding="none"
      aria-label="Setup"
      className="divide-border-subtle grid divide-y overflow-hidden @3xl/main:grid-cols-2 @3xl/main:divide-x @3xl/main:divide-y-0"
    >
      <OptionRow
        icon={<ChromeIcon className="size-5" />}
        title="Chrome Extension"
        href={installed === false ? EXTENSION_INSTALL_URL : undefined}
        external
        line={
          installed === null ? (
            <span className="text-ink-meta">Checking…</span>
          ) : installed ? (
            <span className="text-positive-ink inline-flex items-center gap-1">
              <CheckIcon aria-hidden weight="bold" className="size-3.5" />
              Added
            </span>
          ) : (
            <span className="text-brand font-medium">Add to Chrome</span>
          )
        }
      />
      <OptionRow
        icon={<NotepadIcon aria-hidden className="text-ink-meta size-5" />}
        title="Application Info"
        href="/auto-apply/info"
        line={
          <span className="text-ink-meta">Work authorization, screening answers, transcript</span>
        }
      />
    </Card>
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
