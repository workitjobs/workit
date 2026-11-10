// The edge tab on a job form the student opened themselves (KAN-394):
// manifest.json's one static content script on the job systems' hosts, in
// every frame. Nothing fills here. Most pages on those hosts are no form (a
// job system's own site, a board's list), so the launcher alone runs there
// (KAN-749): it waits for the page's load, asks the background whether the
// page is a job page WorkIt covers (panel/where, the Fill engine's jobOf),
// and stops, with no panel file loaded, no observer and no listener. On a job
// page outside a batch the background loads the panel's files into this frame
// (panel/shell, background.js SHELL_FILES) and the launcher draws only the
// edge tab, with Autofill This Page in the panel behind it. A batch tab's
// panel is the fill's own (overlay.js), so this leaves it alone.
window.WIA = window.WIA || {};

(async function () {
  "use strict";

  if (window.WIA.launched) return;
  // iCIMS's frame inside its own top page: the panel is the top page's (icims.js).
  if (window.top !== window && /(^|\.)icims\.com$/.test(location.hostname) && (() => { try { return parent.location.hostname === location.hostname; } catch { return false; } })()) return;
  window.WIA.launched = true;
  const send = (message) => Promise.resolve(chrome.runtime.sendMessage(message)).catch(() => null);
  // After the page's own start-up: a node Greenhouse's React didn't render, drawn while it starts, makes it
  // draw the form again (overlay.js, "the panel goes on the page once the fill is done").
  if (document.readyState !== "complete") await new Promise((done) => addEventListener("load", done, { once: true }));
  await new Promise((done) => setTimeout(done, 1000));
  const fillOwns = () => window.WIA.running || window.WIA.batch || window.WIA.overlay?.state?.();
  if (fillOwns()) return;
  const where = await send({ type: "panel/where" });
  if (!where?.job || where.batch || fillOwns()) return;
  if (!window.WIA.panel && !(await send({ type: "panel/shell" }))?.loaded) return;
  const panel = window.WIA.panel;
  await panel.where(where);
  await panel.ensure();
  if (fillOwns()) return;
  // Autofill This Page, or Sign in to WorkIt when signed out (panel-states.js, KAN-401).
  if (!window.WIA.overlay?.state?.()) await window.WIA.panelStates.start();
  panel.showEdge();
})();
