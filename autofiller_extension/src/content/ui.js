// The panel's small shared helpers, loaded before every other panel and fill
// file (shared/content-scripts.js: SHELL_FILES, CONTENT_SCRIPT_FILES):
//
// - ask(message): chrome.runtime.sendMessage, rejecting as it does.
// - send(message): the same, but a failed send answers null.
// - el(tag, className, text) and button(label, onPress): the panel's nodes.
// - copy(text): the text to the student's clipboard (a page that blocks the
//   clipboard API gets the older copy command).
// - trusted(onPress): a click listener that acts on the student's own clicks
//   only (event.isTrusted). The panel lives in the employer's page, whose
//   scripts can dispatch clicks; every click listener in the panel takes its
//   clicks through this (button() does), down to a fold or a Not Now
//   (KAN-469). The one exception is submit-warning.js's watch on the
//   employer's own Submit, which holds the page's clicks too.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  if (window.WIA.ui) return;

  const ask = (message) => chrome.runtime.sendMessage(message);
  const send = (message) => Promise.resolve(chrome.runtime.sendMessage(message)).catch(() => null);

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const trusted = (onPress) => (event) => (event?.isTrusted ? onPress(event) : undefined);

  const button = (label, onPress) => {
    const node = el("button", null, label);
    node.type = "button";
    node.addEventListener("click", trusted(onPress));
    return node;
  };

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const box = Object.assign(document.createElement("textarea"), { value: text });
      document.body.append(box);
      box.select();
      document.execCommand("copy");
      box.remove();
    }
  };

  window.WIA.ui = { ask, send, el, button, trusted, copy };
})();
