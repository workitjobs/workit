// Trusted text and choices for plain Workers (KAN-716): the text Apply and Lisul's tile type, as a
// keyboard's, and the radios and checkboxes Apply clicks, as a mouse's.
//
// Every other input a plain Worker makes is a synthetic DOM event or an editing command, and
// neither fires what a keyboard fires: execCommand("insertText") gives an `input` but no
// `beforeinput` and no `textInput`. amazon.jobs's text boxes showed such text but never took it
// (its "This field is required" stayed, its auto-save failed, a reload emptied the box), and a
// reload showed blank the radios a synthetic click had set. So these go in through chrome.debugger.
//
// What this may send, and nothing else (`send` refuses the rest, parameter by parameter):
// - Input.insertText: text at the caret of the field that has the focus, never with a line break
//   (a lone "\n" in a one-line box is an Enter to Blink, and submits its form). It is no key: it
//   can't press Enter, click or activate a button. In a box that isn't editable it does nothing.
// - Input.dispatchKeyEvent for Backspace and Delete only, with no text and no modifiers: they
//   delete in a field and do nothing anywhere else.
// - Input.dispatchMouseEvent: one plain left press and release at a point in the top frame, only
//   for a choice page/dom.js named (a radio, a checkbox or an option, never a button or a link, or
//   anything inside one), with no move before it for a page to time a change by.
// - Emulation.setFocusEmulationEnabled {enabled: true}: the tab acts as focused while it is
//   attached, as Playwright's CDP pages do, so the field hears its focus and blur.
//
// Around each one (`finish`): page/dom.js's `aim` checks, just before it, that the request is its
// own and still holds (the field has the focus; the choice alone is under the point); every other
// frame of the tab refuses trusted input until it is over (`fence`); and `landed` checks the
// effect after it (the text arrived; the click reached the choice and changed it). A miss is an
// error for Apply, never a second try. The submit guard and its network rules stand behind all of
// it.
//
// The debugger attachment is debug.js's, shared with cdp.js: a tab detaches a few seconds after
// its last input unless cdp.js keeps it. Workers start with --silent-debugger-extension-api
// (apply.plain.launcher), so Chrome shows no "started debugging this browser" bar. Without the
// debugger (no permission, a DevTools window on the tab, a chrome:// page) page/dom.js acts as
// before, untrusted.

import { attach as attachTab, available } from "./debug.js";
import { named } from "./shared.js";

const KEYS = {
  Backspace: { code: "Backspace", windowsVirtualKeyCode: 8, commands: ["deleteBackward"] },
  Delete: { code: "Delete", windowsVirtualKeyCode: 46, commands: ["deleteForward"] },
};
const MOUSE = new Set(["mousePressed", "mouseReleased"]);

export { available };

const exactly = (params, keys) => Object.keys(params ?? {}).sort().join() === [...keys].sort().join();

function allowed(method, params) {
  if (method === "Input.insertText") return exactly(params, ["text"]) && typeof params.text === "string" && params.text !== "" && !/[\r\n]/.test(params.text);
  if (method === "Input.dispatchKeyEvent") {
    const key = KEYS[params?.key];
    if (!key || !/^(rawKeyDown|keyUp)$/.test(params.type)) return false;
    const commands = params.type === "keyUp" ? [] : key.commands;
    return exactly(params, ["type", "key", "code", "windowsVirtualKeyCode", "commands"]) && params.code === key.code &&
      params.windowsVirtualKeyCode === key.windowsVirtualKeyCode && JSON.stringify(params.commands) === JSON.stringify(commands);
  }
  if (method === "Input.dispatchMouseEvent")
    return exactly(params, ["type", "x", "y", "button", "clickCount", "buttons"]) && MOUSE.has(params.type) && params.button === "left" &&
      params.clickCount === 1 && params.buttons === (params.type === "mousePressed" ? 1 : 0) && Number.isFinite(params.x) && Number.isFinite(params.y);
  if (method === "Emulation.setFocusEmulationEnabled") return exactly(params, ["enabled"]) && params.enabled === true;
  return false;
}

// The one place trusted input leaves this extension (cdp.js sends page code through its own list).
export function send(tab, method, params) {
  if (!allowed(method, params)) return Promise.reject(named("Refused", `the worker extension sends no debugger command ${method} ${JSON.stringify(params)}`));
  return chrome.debugger.sendCommand({ tabId: tab }, method, params);
}

// The shared attachment, with focus emulation on once per attachment, as before.
async function attach(tab) {
  const entry = await attachTab(tab);
  if (!entry.focus) {
    await send(tab, "Emulation.setFocusEmulationEnabled", { enabled: true });
    entry.focus = true;
  }
}

// Every frame of the tab but `frame` refuses trusted input (`on`) or takes it again: a page that
// moves the focus or another frame under the point mid-way gets nothing there.
function fenceFrame(on) {
  const KINDS = ["beforeinput", "pointerdown", "mousedown", "pointerup", "mouseup", "click", "auxclick", "dblclick", "contextmenu"];
  const old = globalThis.__applyFence;
  if (old) for (const kind of KINDS) removeEventListener(kind, old, true);
  globalThis.__applyFence = null;
  if (!on) return;
  const refuse = (event) => {
    if (!event.isTrusted) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  };
  globalThis.__applyFence = refuse;
  for (const kind of KINDS) addEventListener(kind, refuse, true);
}

async function fence(params, on) {
  const frame = params.frame ?? 0;
  const others = ((await chrome.webNavigation.getAllFrames({ tabId: params.tab }).catch(() => [])) ?? [])
    .map((f) => f.frameId).filter((id) => id !== frame);
  if (!others.length) return;
  await chrome.scripting.executeScript({ target: { tabId: params.tab, frameIds: others }, world: "ISOLATED", func: fenceFrame,
                                         args: [on], injectImmediately: true }).catch(() => {});
}

async function click(params, { x, y }) {
  if ((params.frame ?? 0) !== 0) throw named("Refused", "a trusted click is for the top frame only");
  await send(params.tab, "Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1, buttons: 1 });
  await send(params.tab, "Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1, buttons: 0 });
}

async function key(tab, name) {
  const { code, windowsVirtualKeyCode, commands } = KEYS[name];
  await send(tab, "Input.dispatchKeyEvent", { type: "rawKeyDown", key: name, code, windowsVirtualKeyCode, commands });
  await send(tab, "Input.dispatchKeyEvent", { type: "keyUp", key: name, code, windowsVirtualKeyCode, commands: [] });
}

// Text with its line breaks between trusted runs: each break untrusted, by page/dom.js (`lineBreak`).
async function text(params, value, token, call) {
  for (const part of value.split(/(\r\n|\r|\n)/)) {
    if (part === "") continue;
    if (/^[\r\n]+$/.test(part)) {
      const broke = await call("lineBreak", [token]);
      if (broke?.ok?.why) throw named("Lost", broke.ok.why);
    } else await send(params.tab, "Input.insertText", { text: part });
  }
}

const asks = (value) => value && typeof value === "object" && ("__applyType" in value || "__applyKey" in value || "__applyKeys" in value || "__applyClick" in value);
const failed = (message) => ({ err: { name: "Error", message: `KAN-716 trusted input: ${message}` } });

// A dom answer, with the trusted input it asks for made: page/dom.js answers {__applyType: text,
// token, after?} (text to insert at its chosen field), {__applyKey: name, token} (Backspace or
// Delete there), {__applyClick: {x, y}, token} (a choice's click) or {__applyKeys: text, chosen}
// (press_sequentially: each character its own key, into the field `chosen` names, while it has the
// focus). `call(method, args)` runs a dom method in the same frame. The answer becomes {ok: null},
// {retry} (a click whose point no longer holds only its choice: Apply tries it again) or an error.
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
  let ready = false;
  try {
    await attach(params.tab);
    ready = true;
  } catch (error) {
    console.warn("Apply worker: no debugger here, untrusted as before", String(error?.message ?? error));
  }
  let tried = false;
  let lost = "";
  if (ready) {
    await fence(params, true);
    try {
      const aimed = await call("aim", [value.token]); // its own request, and it still holds: else nothing is sent
      if (!aimed?.ok?.aimed) {
        await fence(params, false);
        const why = aimed?.ok?.why ?? aimed?.err?.message ?? "no answer";
        return "__applyClick" in value ? { retry: `waiting for the choice alone under the point (${why})` } : failed(why);
      }
      tried = true;
      if ("__applyClick" in value) await click(params, value.__applyClick);
      else if ("__applyKey" in value) await key(params.tab, value.__applyKey);
      else await text(params, value.__applyType, value.token, call);
    } catch (error) {
      if (error?.name === "Lost") lost = error.message;
      else console.warn("Apply worker: a trusted command failed", String(error?.message ?? error));
    } finally {
      await fence(params, false);
    }
  }
  const landed = await call("landed", [value.token, tried]);
  if (!landed || !("ok" in landed)) return landed;
  if (lost || landed.ok?.missed) return failed(lost || landed.ok.missed);
  if (value.after) {
    const after = await call(value.after[0], value.after[1]);
    if (!after || !("ok" in after)) return after;
  }
  return { ok: null };
}
