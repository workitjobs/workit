// Page code and early scripts through chrome.debugger (KAN-839, the W6 spike in
// docs/desktop_application_auto_apply.md).
//
// The Chrome Web Store lets an extension run code that is not in its package only through the
// Debugger API or the User Scripts API, and the User Scripts API is for code the user writes. So a
// store copy of this extension can't run Apply's page code with chrome.userScripts (core.js
// `eval`), and can't load files Apply writes into its folder (vendor/). These ops run that code
// through the debugger instead:
//
// - `cdp.eval`: one expression in a frame's MAIN world. The top frame and a frame from another
//   site (its own process, its own debugger session) take Runtime.evaluate; a same-site frame
//   takes Runtime.callFunctionOn on its document, which DOM.resolveNode gives in the frame's main
//   world. The page's CSP doesn't govern either.
// - `cdp.load`: a whole script (the Fill engine) in a frame's MAIN world, the same way.
// - `cdp.script`: an early script, before the page's own code, in every frame of the tab and of
//   each frame from another site as it starts (Chrome holds a new one until it has the scripts).
//   Not for the guards: a pop-up the page opens is a new tab, which no early script of this tab
//   reaches (measured, KAN-839), while a registered content script reaches every tab.
// - `cdp.keep`: a script held in this service worker's memory, never on disk, by name. Apply hands
//   over the Fill engine once per connection, and engine.js's `engine.load` runs it from here.
//
// Runtime is never turned on (no Runtime.enable, Debugger.enable or Console.enable): with it on,
// DevTools reads each console call's arguments, which a page can notice. `send` refuses every
// command outside ALLOWED.

import { attach, keep, onDetach, onEvent } from "./debug.js";
import { named, untilNavigated } from "./shared.js";

const ALLOWED = new Set([
  "Runtime.evaluate", "Runtime.callFunctionOn", "Runtime.releaseObject", "Runtime.runIfWaitingForDebugger",
  "DOM.getFrameOwner", "DOM.describeNode", "DOM.resolveNode",
  "Page.enable", "Page.getFrameTree", "Page.addScriptToEvaluateOnNewDocument", "Page.removeScriptToEvaluateOnNewDocument",
  "Target.setAutoAttach",
]);
// Frames from another site attach as they start, and wait for their scripts; nothing else attaches.
const AUTO = { autoAttach: true, waitForDebuggerOnStart: true, flatten: true, filter: [{ type: "iframe" }, { exclude: true }] };

const held = new Map(); // name -> source, from `cdp.keep`
const tabs = new Map(); // tab -> {scripts: Map(id -> source), main: Map(id -> identifier), children: Map(sessionId -> targetId)}

function send(target, method, params = {}) {
  if (!ALLOWED.has(method)) return Promise.reject(named("Refused", `the worker extension sends no debugger command ${method}`));
  return chrome.debugger.sendCommand(target, method, params);
}

onDetach((tab) => tabs.delete(tab));

onEvent(async (source, method, params) => {
  const state = tabs.get(source.tabId);
  if (!state) return;
  if (method === "Target.attachedToTarget") {
    const child = { tabId: source.tabId, sessionId: params.sessionId };
    if (params.targetInfo?.type === "iframe") {
      state.children.set(params.sessionId, params.targetInfo.targetId);
      if (state.scripts.size) await send(child, "Page.enable").catch(() => {});
      for (const script of state.scripts.values()) {
        await send(child, "Page.addScriptToEvaluateOnNewDocument", { source: script, runImmediately: true }).catch((error) =>
          console.warn("Apply worker: an early script missed a frame", String(error?.message ?? error)));
      }
      await send(child, "Target.setAutoAttach", AUTO).catch(() => {});
    }
    if (params.waitingForDebugger) await send(child, "Runtime.runIfWaitingForDebugger").catch(() => {});
  } else if (method === "Target.detachedFromTarget") {
    state.children.delete(params.sessionId);
  }
});

// The tab attached, with frames from another site attaching as they start.
async function ready(tab) {
  await attach(tab);
  let state = tabs.get(tab);
  if (!state) {
    state = { scripts: new Map(), main: new Map(), children: new Map(), auto: null };
    tabs.set(tab, state);
  }
  state.auto ??= send({ tabId: tab }, "Target.setAutoAttach", AUTO).catch((error) => {
    state.auto = null;
    throw error;
  });
  await state.auto;
  return state;
}

const flatten = (tree, parent = null, out = []) => {
  out.push({ id: tree.frame.id, url: tree.frame.url + (tree.frame.urlFragment ?? ""), parent });
  for (const child of tree.childFrames ?? []) flatten(child, tree.frame.id, out);
  return out;
};

const sameUrl = (a, b) => (a || "").split("#")[0] === (b || "").split("#")[0];

// Where frame `frame` (a webNavigation frame id) of `tab` runs MAIN-world code: {target} for
// Runtime.evaluate, or {target, objectId} (its document, in its main world) for callFunctionOn.
async function locate(tab, state, frame) {
  if (!frame) return { target: { tabId: tab } };
  const info = await chrome.webNavigation.getFrame({ tabId: tab, frameId: frame });
  if (!info) throw named("NoFrame", `no frame ${frame} in tab ${tab}`);
  const parent = info.parentFrameId > 0 ? await chrome.webNavigation.getFrame({ tabId: tab, frameId: info.parentFrameId }) : null;
  const top = await chrome.tabs.get(tab);
  const parentUrl = parent ? parent.url : top.url;
  // A frame from another site: its own session, whose top document is the frame.
  const away = [];
  for (const sessionId of state.children.keys()) {
    const target = { tabId: tab, sessionId };
    const href = await send(target, "Runtime.evaluate", { expression: "location.href", returnByValue: true }).catch(() => null);
    if (sameUrl(href?.result?.value, info.url)) away.push(target);
  }
  if (away.length === 1) return { target: away[0] };
  // A same-site frame: in the tab's own frame tree, by its URL and its parent's.
  const frames = flatten((await send({ tabId: tab }, "Page.getFrameTree")).frameTree);
  const byId = new Map(frames.map((f) => [f.id, f]));
  const near = frames.filter((f) => f.parent && sameUrl(f.url, info.url) && sameUrl(byId.get(f.parent)?.url, parentUrl));
  if (near.length !== 1) {
    throw named(near.length ? "Ambiguous" : "NoFrame",
                `frame ${frame} (${info.url}) is ${near.length} frames in the debugger's tree and ${away.length} out-of-process ones`);
  }
  const owner = await send({ tabId: tab }, "DOM.getFrameOwner", { frameId: near[0].id });
  const described = await send({ tabId: tab }, "DOM.describeNode", { backendNodeId: owner.backendNodeId, depth: 1, pierce: true });
  const document = described.node?.contentDocument;
  if (!document) throw named("NoFrame", `frame ${frame} (${info.url}) has no document the debugger can reach`);
  const resolved = await send({ tabId: tab }, "DOM.resolveNode", { backendNodeId: document.backendNodeId });
  return { target: { tabId: tab }, objectId: resolved.object.objectId };
}

function thrown(reply) {
  const details = reply.exceptionDetails;
  const message = details.exception?.description ?? details.exception?.value ?? details.text ?? "error";
  return named("EvalError", String(message));
}

// `body` in the frame's MAIN world: an expression (`expression`) or a whole script (not).
async function run(params, body, expression) {
  const state = await ready(params.tab);
  const at = await locate(params.tab, state, params.frame ?? 0);
  let reply;
  if (at.objectId) {
    const declaration = expression ? `function () { return (\n${body}\n); }` : `function () {\n${body}\n}`;
    try {
      reply = await untilNavigated(params, send(at.target, "Runtime.callFunctionOn",
        { objectId: at.objectId, functionDeclaration: declaration, awaitPromise: true, returnByValue: true }));
    } finally {
      send(at.target, "Runtime.releaseObject", { objectId: at.objectId }).catch(() => {});
    }
  } else {
    reply = await untilNavigated(params, send(at.target, "Runtime.evaluate", { expression: body, awaitPromise: true, returnByValue: true, ...(params.gesture === true ? { userGesture: true } : {}) }));
  }
  if (reply.exceptionDetails) throw thrown(reply);
  return reply.result?.value ?? null;
}

// One expression (Apply wraps the caller's code so it answers {ok}, {undef} or {err}, as for `eval`).
// `gesture: true` runs it as if the user had just clicked, so a test can open a pop-up; Apply's own
// code never sends it (apply.plain.script.evaluate).
const evaluate = (params) => run(params, params.code, true);

// A whole script, given (`source`) or held (`name`), run once in the frame.
export async function load(params) {
  const source = params.name ? held.get(params.name) : params.source;
  if (typeof source !== "string") throw named("BadOp", `no script ${params.name ?? "given"} to load`);
  await run(params, source, false);
  return { loaded: true };
}

export const holds = (name) => held.has(name);

async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// A script to hold by name, refused when its sha256 isn't the one Apply sent beside it.
async function hold({ name, source, sha256: sha }) {
  if (!name || typeof source !== "string" || !sha) throw named("BadOp", "cdp.keep needs a name, a source and its sha256");
  if ((await sha256(source)) !== sha) throw named("BadOp", `cdp.keep: ${name}'s sha256 differs from the one sent`);
  held.set(name, source);
  return { name, bytes: source.length };
}

// An early script in every frame of the tab, kept until `cdp.unscript` or the tab closes.
async function script({ tab, id, source }) {
  if (!id || typeof source !== "string") throw named("BadOp", "cdp.script needs an id and a source");
  const state = await ready(tab);
  await keep(tab, "cdp.script");
  if (state.main.has(id)) await unscript({ tab, id });
  state.scripts.set(id, source);
  await send({ tabId: tab }, "Page.enable");
  const added = await send({ tabId: tab }, "Page.addScriptToEvaluateOnNewDocument", { source, runImmediately: true });
  state.main.set(id, added.identifier);
  for (const sessionId of state.children.keys()) {
    await send({ tabId: tab, sessionId }, "Page.enable").catch(() => {});
    await send({ tabId: tab, sessionId }, "Page.addScriptToEvaluateOnNewDocument", { source, runImmediately: true }).catch(() => {});
  }
  return { id, frames: 1 + state.children.size };
}

async function unscript({ tab, id }) {
  const state = tabs.get(tab);
  if (!state) return null;
  const identifier = state.main.get(id);
  state.scripts.delete(id);
  state.main.delete(id);
  if (identifier) await send({ tabId: tab }, "Page.removeScriptToEvaluateOnNewDocument", { identifier }).catch(() => {});
  if (!state.scripts.size) await keep(tab, "cdp.script", false);
  return null;
}

// What the debugger holds on a tab, for tests and the spike's notes.
async function status({ tab }) {
  const state = tabs.get(tab);
  return { attached: Boolean(state), scripts: state ? [...state.scripts.keys()] : [], children: state ? state.children.size : 0 };
}

export const ops = { "cdp.eval": evaluate, "cdp.load": load, "cdp.keep": hold, "cdp.script": script, "cdp.unscript": unscript, "cdp.status": status };
