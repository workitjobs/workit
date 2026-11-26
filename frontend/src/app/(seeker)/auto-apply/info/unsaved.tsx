"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import {
  DiscardBar,
  UnsavedChangesProvider,
  useHasUnsaved,
  useLeaveGuard,
  usePendingLeave,
} from "../../settings/unsaved-changes";
import { INFO_ROOT, partHref, partOf, type InfoPartKey } from "./sections";

/**
 * Application Info's guard against losing edits (2026-11-24): Settings'
 * own (../../settings/unsaved-changes.tsx), since its cards are open forms
 * now, as Settings' are. A form reports its unsaved changes
 * (`useUnsavedChanges`); a move between parts loses nothing, since every
 * part stays mounted (./info-part.tsx); a way out of the page asks
 * "Discard Your Changes?" first, in the bar under the cards.
 *
 * A PAGE HAS NO ONE DOOR TO GUARD, as a modal has its close. Next's router
 * gives a page no way to hold a navigation, so the guard catches the click
 * on any link that leaves Application Info (the rail, the section's tabs,
 * a link in a card) before the link's own handler, and only while
 * something is unsaved: with nothing to lose, the link works as it always
 * does.
 *
 * THE QUESTION OPENS THE PART IT IS ABOUT (`showUnsaved`). The parts stay
 * mounted, so the changes can be on a part that is not the open one: a
 * student changed Work Authorization, looked at Self-Identification, then
 * clicked Queue, and the bar asked about changes nowhere on screen. A form
 * with changes marks itself `data-unsaved`; when the open part has none,
 * the first part that has opens before the bar asks. Closing the tab or a reload gets the browser's own warning. Not
 * caught, as in Settings: the browser's Back, and a move a button makes
 * with no link.
 */
export function InfoUnsaved({ children }: { children: ReactNode }) {
  return (
    <UnsavedChangesProvider>
      <LinkGuard />
      {children}
    </UnsavedChangesProvider>
  );
}

function LinkGuard() {
  const router = useRouter();
  const guard = useLeaveGuard();
  const hasUnsaved = useHasUnsaved();

  useEffect(() => {
    function onClick(event: MouseEvent) {
      // A modified click opens another tab; this page stays.
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = (event.target as Element | null)?.closest?.<HTMLAnchorElement>("a[href]");
      if (!link || link.target === "_blank" || link.origin !== window.location.origin) return;
      const inside = link.pathname === INFO_ROOT || link.pathname.startsWith(`${INFO_ROOT}/`);
      if (inside || !hasUnsaved()) return;
      event.preventDefault();
      event.stopPropagation();
      showUnsaved();
      const href = `${link.pathname}${link.search}${link.hash}`;
      guard(() => router.push(href));
    }
    // Capture: ahead of the link's own handler, which would navigate.
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [router, guard, hasUnsaved]);

  return null;
}

/** Opens the first part that holds unsaved changes, unless the open part
 *  holds some: the menu's own move, in place (./info-nav.tsx). */
function showUnsaved() {
  const parts = [...document.querySelectorAll<HTMLElement>("[data-unsaved]")]
    .map((form) => form.closest<HTMLElement>("[data-info-part]")?.dataset.infoPart)
    .filter((part): part is InfoPartKey => part != null);
  const open = partOf(window.location.pathname);
  if (parts.length === 0 || (open && parts.includes(open))) return;
  window.history.replaceState(null, "", partHref(parts[0]));
  document.getElementById("content")?.scrollTo({ top: 0 });
}

/**
 * The question, under the cards: Settings' bar (`DiscardBar`), drawn as a
 * card of its own that stays at the foot of the screen while it is asked,
 * so the edits it asks about stay in view above it. Escape keeps editing,
 * as in Settings.
 */
export function InfoDiscardBar() {
  const { asking, keep } = usePendingLeave();

  useEffect(() => {
    if (!asking) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && keep();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [asking, keep]);

  if (!asking) return null;
  return (
    <div className="border-border-surface rounded-card shadow-panel sticky bottom-4 z-20 overflow-hidden border *:border-t-0">
      <DiscardBar />
    </div>
  );
}
