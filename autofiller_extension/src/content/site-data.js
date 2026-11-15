// A job system's selectors and patterns for the extension's own page scripts
// (KAN-778): the stepped systems' walk (workday.js, oracle.js, icims.js,
// successfactors.js, workday-walk.js, primary.js) and the panel's Workday
// step line (panel-top.js). They read the Rules table's names for their job
// system, as the engine does, never a copy of their own, so the Store package
// (which ships no job system's data, KAN-777) carries none.
//
// The data is the engine's for the page's job system (FillEngine.siteRules in
// the background: the served table's, else the bundled one), which the
// background puts here, in the isolated world's memory only, before the
// panel's shell and before every fill (shared/content-scripts.js
// `giveSiteData`). `window.WIA.site(site)` reads it by name at each use, never
// at load: `SEL.NAME` is a selector string, `PAT.NAME` a compiled RegExp.
// A name the data lacks (another job system's page, or the Store package with
// no table yet) is a selector that matches nothing and a pattern that matches
// nothing, so a script finds nothing rather than throwing. Each list is used
// whole (a served copy's lists are watermarked: reordered, with a decoy part).
// First of the panel's shell (SHELL_FILES), so every script after it has it.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  if (window.WIA.site) return;
  const NO_SELECTOR = ":not(*)";
  const NO_PATTERN = /(?!)/;
  const compiled = new Map();

  /** The data the background gave for `site`, or null. */
  const dataOf = (site) => (window.WIA.siteData?.site === site ? window.WIA.siteData.data ?? null : null);

  /** A pattern `{source, flags}` as a RegExp, compiled once. */
  function compile(pattern) {
    const id = `${pattern.flags ?? ""}/${pattern.source}`;
    if (!compiled.has(id)) compiled.set(id, new RegExp(pattern.source, pattern.flags ?? ""));
    return compiled.get(id);
  }

  const reader = (read) => new Proxy({}, { get: (_, name) => (typeof name === "string" ? read(name) : undefined) });

  /** `site`'s names: `SEL.NAME` (a selector or wording), `PAT.NAME` (a RegExp). */
  window.WIA.site = (site) => ({
    SEL: reader((name) => dataOf(site)?.strings?.[name] ?? NO_SELECTOR),
    PAT: reader((name) => {
      const pattern = dataOf(site)?.patterns?.[name];
      return pattern ? compile(pattern) : NO_PATTERN;
    }),
  });
})();
