"use client";

import { useSyncExternalStore, type ReactNode } from "react";

import { SessionProbe } from "./session-swap";

/** Where the bar is: at the page's top, floating as a panel, or hidden. */
type Place = "top" | "floating" | "hidden";

/** Below this the bar always shows, so the hero never loses its header. */
const SHOW_ABOVE = 96;
/** How far the page must move one way before the bar hides or shows, so a
 *  trackpad's small back-and-forth does not flicker it. */
const STEP = 6;

let place: Place = "top";
let lastY = 0;

/** Reads the scroll: past the top, a scroll down hides the bar and a scroll
 *  up shows it. Small moves add up until they pass `STEP`. */
function read() {
  const y = Math.max(0, window.scrollY);
  if (y <= SHOW_ABOVE) {
    place = y > 8 ? "floating" : "top";
    lastY = y;
  } else if (y > lastY + STEP) {
    place = "hidden";
    lastY = y;
  } else if (y < lastY - STEP) {
    place = "floating";
    lastY = y;
  }
}

function subscribe(onChange: () => void) {
  const onScroll = () => {
    read();
    onChange();
  };
  read();
  window.addEventListener("scroll", onScroll, { passive: true });
  return () => window.removeEventListener("scroll", onScroll);
}

/**
 * The landing header's outer element. It marks itself `data-scrolled` once
 * the page leaves the top, so header.tsx can give the bar its white fill
 * and foot line with `group-data-scrolled:` classes, and `data-hidden` while
 * the reader scrolls down, so the bar slides up out of the way and comes
 * back on the first scroll up (the user's ask, KAN-923, 2026-11-20). It
 * stays while a menu is open or focus is inside it (`.site-header` in
 * landing.css), so a keyboard visitor never tabs into a hidden bar. Server
 * render and first paint are unscrolled. It also mounts the header's
 * SessionProbe (KAN-581).
 */
export function FloatingHeader({ children }: { children: ReactNode }) {
  const now = useSyncExternalStore(
    subscribe,
    () => place,
    () => "top" as Place,
  );
  return (
    <header
      data-scrolled={now !== "top" || undefined}
      data-hidden={now === "hidden" || undefined}
      className="site-header group sticky top-0 z-40"
    >
      <SessionProbe />
      {children}
    </header>
  );
}
