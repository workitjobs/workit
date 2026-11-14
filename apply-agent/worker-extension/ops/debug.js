// The one chrome.debugger attachment per tab that every op shares (KAN-839). Chrome lets an
// extension attach to a tab once, so typing.js (trusted input) and cdp.js (page code and early
// scripts through the Debugger API) both go through here.
//
// A tab detaches IDLE ms after its last use, unless an op keeps it (`keep`): cdp.js keeps a tab
// while it holds early scripts there, since a detach drops them. Workers start with
// --silent-debugger-extension-api (apply.plain.launcher), so Chrome shows no "started debugging
// this browser" bar. Nothing here sends a command: each caller sends its own, through its own
// list of allowed commands.

const IDLE = 4000; // ms a tab stays attached after its last use, when nothing keeps it
const tabs = new Map(); // tab -> {ready, timer, kept: Set<string>, focus: boolean}
const events = new Set(); // (source, method, params) listeners
const detaches = new Set(); // (tab) listeners

function forget(tab) {
  const entry = tabs.get(tab);
  if (!entry) return;
  clearTimeout(entry.timer);
  tabs.delete(tab);
  for (const listener of detaches) listener(tab);
}

chrome.debugger?.onDetach?.addListener(({ tabId }) => forget(tabId));
chrome.debugger?.onEvent?.addListener((source, method, params) => {
  for (const listener of events) listener(source, method, params);
});
chrome.tabs.onRemoved.addListener((tab) => forget(tab));

export const available = () => typeof chrome.debugger?.attach === "function";

export const onEvent = (listener) => events.add(listener);
export const onDetach = (listener) => detaches.add(listener);

function idle(tab, entry) {
  clearTimeout(entry.timer);
  if (entry.kept.size) return;
  entry.timer = setTimeout(() => {
    if (tabs.get(tab) !== entry || entry.kept.size) return;
    chrome.debugger.detach({ tabId: tab }).catch(() => {});
    forget(tab);
  }, IDLE);
}

// The tab's attachment, made if needed; its idle timer starts again.
export async function attach(tab) {
  let entry = tabs.get(tab);
  if (!entry) {
    entry = { timer: null, kept: new Set(), focus: false };
    entry.ready = chrome.debugger.attach({ tabId: tab }, "1.3");
    tabs.set(tab, entry);
    entry.ready.catch(() => tabs.get(tab) === entry && tabs.delete(tab));
  }
  await entry.ready;
  idle(tab, entry);
  return entry;
}

// Keep the tab attached for `why` (on), or let it go idle again once nothing keeps it (off).
export async function keep(tab, why, on = true) {
  const entry = on ? await attach(tab) : tabs.get(tab);
  if (!entry) return;
  if (on) entry.kept.add(why);
  else entry.kept.delete(why);
  idle(tab, entry);
}

export const isAttached = (tab) => tabs.has(tab);
