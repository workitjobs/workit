"use client";

import { useSyncExternalStore } from "react";

/**
 * Whether this browser runs on a Mac, for the offers of WorkIt Auto Apply
 * (lib/auto-apply-desktop.ts), which only a Mac can run. False on the server
 * and in the first render, so hydration matches, then the browser's answer.
 * An iPad asking for the desktop site reports a Mac, so a touch screen is
 * not one. Intel Macs can't be told apart and still count: the pages say
 * Apple Silicon.
 */
export function useIsMac(): boolean {
  return useSyncExternalStore(subscribe, isMac, () => false);
}

const subscribe = () => () => {};

function isMac(): boolean {
  const nav = navigator as Navigator & { userAgentData?: { platform?: string } };
  const platform = nav.userAgentData?.platform ?? nav.userAgent;
  return /mac/i.test(platform) && nav.maxTouchPoints <= 1;
}
