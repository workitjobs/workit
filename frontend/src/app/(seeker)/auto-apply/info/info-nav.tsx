"use client";

import { SideNav } from "@/components/side-nav";

import { useInfoPart } from "./info-part";
import { INFO_PARTS, partHref, type InfoPartKey } from "./sections";

/**
 * Application Info's menu (./layout.tsx): the shared side menu
 * (components/side-nav.tsx), Settings' own, and it works as Settings'
 * does. Each item is a real link to its part's address, but a plain click
 * switches the part in place: it moves the address with
 * `history.replaceState`, which Next's router follows, and the part shows
 * at once (./info-part.tsx). No navigation, so the other parts and their
 * unsaved edits stay as they were, and one history entry stands for the
 * whole page.
 *
 * It was a table of contents that scrolled one page of six cards for a
 * day (2026-11-23). No Back at its head and no line at its foot: the tabs
 * over it are the way to the queue, and each card says what it holds.
 */
export function InfoNav() {
  const active = useInfoPart() ?? INFO_PARTS[0].key;

  function select(key: string) {
    window.history.replaceState(null, "", partHref(key as InfoPartKey));
    // The shell's <main> scrolls, not the window: a part opens at its top.
    document.getElementById("content")?.scrollTo({ top: 0 });
  }

  return (
    <SideNav
      label="Application Info"
      items={INFO_PARTS.map(({ key, label, Icon }) => ({
        key,
        label,
        Icon,
        href: partHref(key),
      }))}
      active={active}
      onSelect={select}
    />
  );
}
