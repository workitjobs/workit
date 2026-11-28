// WorkIt Auto Apply Worker. Copyright (c) 2026 its authors. All rights reserved: see LICENSE.
// S1 ops: ping, the Worker's tabs, and page code (eval).

import { keepAcrossReload } from "./guard.js";
import { evaluate as evaluateHere } from "./cdp.js";
import { useVendor } from "./shared.js";

function tabInfo(tab) {
  return { tab: tab.id, url: tab.url || tab.pendingUrl || "", title: tab.title || "", status: tab.status, active: tab.active, window: tab.windowId, opener: tab.openerTabId ?? null };
}

// `code` is one expression (Apply wraps the caller's code so it answers {ok}, {undef} or {err}). It
// runs through the debugger (cdp.js, KAN-839) in the frame's MAIN world, which the page's CSP
// doesn't govern: no chrome.userScripts, which a Chrome Web Store copy may use only for the user's
// own code, and no eval in the page.
const evaluate = (params) => evaluateHere(params);

// `bounds` moved and shrunk to fit the main screen's visible area (under the menu bar, beside the
// Dock), so the whole window is on-screen at a corner: never off-screen, never minimized.
async function onScreen(bounds) {
  if (bounds.width === undefined || !chrome.system?.display) return bounds;
  const displays = await chrome.system.display.getInfo().catch(() => []);
  const area = (displays.find((d) => d.isPrimary) ?? displays[0])?.workArea;
  if (!area) return bounds;
  const left = Math.max(area.left, bounds.left ?? 0);
  const top = Math.max(area.top, bounds.top ?? 0);
  const width = Math.min(bounds.width, area.left + area.width - left);
  const height = Math.min(bounds.height, area.top + area.height - top);
  return { left, top, width, height };
}

export const ops = {
  ping: async () => ({ pong: true, webdriver: navigator.webdriver === true, tabs: (await chrome.tabs.query({})).length }),
  "tabs.query": async () => (await chrome.tabs.query({})).map(tabInfo),
  "tabs.create": async ({ url, active = false }) => tabInfo(await chrome.tabs.create({ url: url || "about:blank", active })),
  // focused: false shows the window without activating Chrome, so it never takes Lisul's focus.
  "windows.create": async ({ url, left, top, width, height }) =>
    tabInfo((await chrome.windows.create({ url: url || "about:blank", focused: false, ...(await onScreen({ left, top, width, height })) })).tabs[0]),
  // The Worker's window to the front: only Lisul's own Show calls it (PlainWorkers.show), on Windows and Linux,
  // where Apply has no FocusKeeper, or on the Mac when FocusKeeper can't (W4, KAN-850).
  "windows.focus": async () => {
    await chrome.windows.update((await chrome.windows.getLastFocused()).id, { focused: true });
    return null;
  },
  "tabs.get": async ({ tab }) => tabInfo(await chrome.tabs.get(tab)),
  "tabs.close": async ({ tab }) => {
    await chrome.tabs.remove(tab);
    return null;
  },
  eval: evaluate,
  // The vendor set Apply's files are in from now (Apply wrote a new one: its Fill engine changed).
  "vendor.use": async ({ root }) => ({ root: useVendor(root) }),
  // Load this extension's files again from its folder (newer code after a checkout), as its
  // reload button does: web tabs, their pages and cookies stay; this port closes and the new
  // code says hello again. The guards come back with it (guard.js: keepAcrossReload). Answers
  // first, then reloads.
  "extension.reload": async () => {
    await keepAcrossReload();
    setTimeout(() => chrome.runtime.reload(), 100);
    return null;
  },
};

export { tabInfo };
