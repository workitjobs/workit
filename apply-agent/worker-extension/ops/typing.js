// Trusted text and choices for plain Workers (KAN-716): the text Apply and Lisul's tile type, as a
// keyboard's, and the radios and checkboxes Apply clicks, as a mouse's.
//
// Every other input a plain Worker makes is a synthetic DOM event or an editing command, and
// neither fires what a keyboard fires: execCommand("insertText") gives an `input` but no
// `beforeinput` and no `textInput`. amazon.jobs's text boxes showed such text but never took it
// (its "This field is required" stayed, its auto-save failed, a reload emptied the box). So the
// text itself goes in through chrome.debugger, as CDP's Input.insertText: the `beforeinput`,
// `textInput` and `input` a person's typing fires, each trusted.
//
// What this may send, and nothing else (`send` refuses the rest):
// - Input.insertText: text at the caret of the field that has the focus. It is no key: it can't
//   press Enter, submit a form, click or activate a button. In a box that isn't editable it does
//   nothing.
// - Input.dispatchKeyEvent for Backspace and Delete only, with no text: they delete in a field and
//   do nothing anywhere else.
// - Input.dispatchMouseEvent: one plain left click (move, press, release) at a point in the top
//   frame, only for a choice page/dom.js named: a radio, a checkbox or an option, never a button
//   or a link, or anything inside one. amazon.jobs dropped radios a synthetic click had set. Until
//   it is in, page/dom.js cancels any trusted press or click that reaches another element, so a
//   page that moves a Submit under the point gets no click.
// - Emulation.setFocusEmulationEnabled {enabled: true}: the tab acts as focused while it is
//   attached, as Playwright's CDP pages do, so the field hears its focus and blur.
// page/dom.js picks the field (the one Apply's call chose, focused), and refuses any trusted
// insertion that reaches another element while one is under way (its `request`).
//
// The debugger is attached to a tab only while text goes in, and detached IDLE ms after the
// last. Workers start with --silent-debugger-extension-api (apply.plain.launcher), so Chrome shows
// no "started debugging this browser" bar. Without the debugger (no permission, a DevTools window
// on the tab, a chrome:// page) page/dom.js types as before, untrusted.

import { named } from "./shared.js";

const IDLE = 4000; // ms the debugger stays on a tab after its last text
const KEYS = {
  Backspace: { code: "Backspace", windowsVirtualKeyCode: 8, commands: ["deleteBackward"] },
  Delete: { code: "Delete", windowsVirtualKeyCode: 46, commands: ["deleteForward"] },
};
const MOUSE = new Set(["mouseMoved", "mousePressed", "mouseReleased"]);
const attached = new Map(); // tab -> {ready, timer}

chrome.debugger?.onDetach?.addListener(({ tabId }) => attached.delete(tabId));
chrome.tabs.onRemoved.addListener((tab) => attached.delete(tab));

export const available = () => typeof chrome.debugger?.attach === "function";

// The one place a debugger command leaves this extension.
export function send(tab, method, params) {
  const ok =
    method === "Input.insertText" ? typeof params?.text === "string" && Object.keys(params).length === 1
    : method === "Input.dispatchKeyEvent" ? KEYS[params?.key] && !("text" in params) && !("unmodifiedText" in params) &&
      /^(rawKeyDown|keyUp)$/.test(params.type) && JSON.stringify(params.commands ?? []) === JSON.stringify(params.type === "keyUp" ? [] : KEYS[params.key].commands)
    : method === "Input.dispatchMouseEvent" ? MOUSE.has(params?.type) && Number.isFinite(params.x) && Number.isFinite(params.y) &&
      params.button === (params.type === "mouseMoved" ? "none" : "left") && (params.clickCount ?? 0) <= 1 && !params.modifiers &&
      Object.keys(params).every((k) => ["type", "x", "y", "button", "clickCount", "buttons"].includes(k))
    : method === "Emulation.setFocusEmulationEnabled" ? params?.enabled === true && Object.keys(params).length === 1
    : false;
  if (!ok) return Promise.reject(named("Refused", `the worker extension sends no debugger command ${method} ${JSON.stringify(params)}`));
  return chrome.debugger.sendCommand({ tabId: tab }, method, params);
}

async function attach(tab) {
  let entry = attached.get(tab);
  if (!entry) {
    entry = { timer: null };
    entry.ready = (async () => {
      await chrome.debugger.attach({ tabId: tab }, "1.3");
      await send(tab, "Emulation.setFocusEmulationEnabled", { enabled: true });
    })();
    attached.set(tab, entry);
    entry.ready.catch(() => attached.get(tab) === entry && attached.delete(tab));
  }
  await entry.ready;
  clearTimeout(entry.timer);
  entry.timer = setTimeout(() => {
    if (attached.get(tab) !== entry) return;
    attached.delete(tab);
    chrome.debugger.detach({ tabId: tab }).catch(() => {});
  }, IDLE);
}

async function insertText(tab, text) {
  await attach(tab);
  await send(tab, "Input.insertText", { text });
}

// One left click at (x, y), CSS pixels of the tab's viewport: only for the top frame's choice that
// page/dom.js named (a radio, a checkbox, an option), which cancels it if it lands anywhere else.
async function click(params, { x, y }) {
  if ((params.frame ?? 0) !== 0) throw named("Refused", "a trusted click is for the top frame only");
  await attach(params.tab);
  await send(params.tab, "Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" });
  await send(params.tab, "Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1, buttons: 1 });
  await send(params.tab, "Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1, buttons: 0 });
}

async function key(tab, name) {
  await attach(tab);
  const { commands, ...rest } = KEYS[name];
  await send(tab, "Input.dispatchKeyEvent", { type: "rawKeyDown", key: name, ...rest, commands });
  await send(tab, "Input.dispatchKeyEvent", { type: "keyUp", key: name, ...rest, commands: [] });
}

const asks = (value) => value && typeof value === "object" && ("__applyType" in value || "__applyKey" in value || "__applyKeys" in value || "__applyClick" in value);

// A dom answer, with the trusted text it asks for typed: page/dom.js answers {__applyType: text,
// token, after?} (text to insert at its chosen field), {__applyKey: name, token} (Backspace or
// Delete there) or {__applyKeys: text, chosen} (press_sequentially: each character its own key,
// into the field `chosen` names, while it has the focus).
// `call(method, args)` runs a dom method in the same frame. The answer becomes {ok: null}.
export async function finish(params, answer, call) {
  const value = answer?.ok;
  if (!asks(value)) return answer;
  if ("__applyKeys" in value) {
    try {
      for (const character of value.__applyKeys) {
        const typed = await call("keyInto", [value.chosen, character]);
        if (typed?.ok?.stop) break; // the field lost the focus: the rest goes nowhere
        const one = await finish(params, typed, call);
        if (!one || !("ok" in one)) return one;
      }
    } finally {
      await call("keyInto", [value.chosen, null]).catch(() => {});
    }
    return { ok: null };
  }
  let tried = false;
  try {
    if ("__applyClick" in value) await click(params, value.__applyClick);
    else if ("__applyKey" in value) await key(params.tab, value.__applyKey);
    else await insertText(params.tab, value.__applyType);
    tried = true;
  } catch (error) {
    console.warn("Apply worker: no trusted text here, typing as before", String(error?.message ?? error));
  }
  const landed = await call("landed", [value.token, tried]);
  if (!landed || !("ok" in landed)) return landed;
  if (value.after) {
    const after = await call(value.after[0], value.after[1]);
    if (!after || !("ok" in after)) return after;
  }
  return { ok: null };
}
