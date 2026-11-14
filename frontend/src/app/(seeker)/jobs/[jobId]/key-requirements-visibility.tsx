"use client";

import { TargetIcon } from "@phosphor-icons/react/ssr";
import { useId, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

const PREFERENCE_KEY = "workit:key-requirements-hidden";
const CHANGE_EVENT = "workit:key-requirements-visibility";
let fallbackHidden: boolean | null = null;

function subscribe(onChange: () => void) {
  function onStorage(event: StorageEvent) {
    if (event.key !== null && event.key !== PREFERENCE_KEY) return;
    fallbackHidden = null;
    onChange();
  }
  window.addEventListener("storage", onStorage);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

function getSnapshot() {
  if (fallbackHidden !== null) return fallbackHidden;
  try {
    return window.localStorage.getItem(PREFERENCE_KEY) === "true";
  } catch {
    return false;
  }
}

function getServerSnapshot() {
  return false;
}

export function KeyRequirementsVisibility({ children }: { children: ReactNode }) {
  const hidden = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const contentId = useId();
  const titleId = useId();

  function toggle() {
    fallbackHidden = !hidden;
    try {
      window.localStorage.setItem(PREFERENCE_KEY, String(!hidden));
    } catch {
      // Keep the control usable when the browser blocks persistent storage.
    }
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }

  // A section of the job's panel (`JobPanel`, ./job-view.tsx), not a card
  // of its own (2026-11-10): its heading is drawn as the description's
  // sections' are (./description.tsx, `Heading`), 20px bold beside a 24px
  // brand glyph, since the two sit one under the other in the same panel.
  // As a 16px card title above 20px section headings it read upside down.
  return (
    <section aria-labelledby={titleId}>
      <div className="flex items-center justify-between gap-4">
        <h2 id={titleId} className="text-title text-ink flex items-center gap-2 font-bold">
          <TargetIcon aria-hidden className="text-brand size-6 shrink-0" />
          Key Requirements
        </h2>
        <Button
          variant="section"
          onClick={toggle}
          aria-expanded={!hidden}
          aria-controls={contentId}
          aria-label={hidden ? "Show Key Requirements" : "Hide Key Requirements"}
        >
          {hidden ? "Show" : "Hide"}
        </Button>
      </div>
      <div id={contentId} hidden={hidden}>
        {children}
      </div>
    </section>
  );
}
