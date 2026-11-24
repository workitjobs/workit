// iCIMS's career sites (<tenant>.icims.com), for the fill (content-script.js):
// which step shows, when it has settled, and the candidate's sign-in. iCIMS
// draws every page in its own iframe (#icims_content_iframe, same host), so
// this reads that frame's document (`doc`), as the engine's icims.ts does,
// and the panel stays on the top page. The sign-in (email, the privacy
// consent and its "I accept" box, then a password or a new login) is the
// student's: WorkIt never types into it or presses its Next. The panel tells
// them to sign in; each step fills once it shows. A step is a new page in the
// frame, which the top page's observers don't see, so the waits here look
// every STEP_LOOK ms. The same face as workday.js gives (see steps.js);
// loaded after oracle.js, as window.WIA.icims. iCIMS's selectors and
// patterns are the Rules table's (site-data.js: SEL, PAT), read at each use.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  const { SEL, PAT } = window.WIA.site("icims");
  // How often a wait looks at the frame, how long a step must stop changing before it is read, and the longest wait for that.
  const STEP_LOOK = 300;
  const STEP_QUIET = 600;
  const STEP_QUIET_MAX = 10_000;
  const FILLED_STEPS = "workit-icims-filled";
  const oneLine = (text) => String(text ?? "").replace(/\s+/g, " ").trim();
  const shows = (el) => Boolean(el) && el.checkVisibility?.() !== false && (el.offsetParent !== null || el.getClientRects().length > 0);
  const text = (el) => (el ? oneLine(el.innerText ?? el.textContent).replace(/\s*\*\s*$/, "").replace(/\s*\(required\)$/i, "") : "");

  /** Whether this is iCIMS's frame inside its own top page (the top page fills it). */
  function nested() {
    if (window.top === window) return false;
    try { return window.parent.location.hostname === location.hostname; } catch { return false; }
  }
  const isOn = /(^|\.)icims\.com$/.test(location.hostname) && !nested();

  /** The document iCIMS draws its pages in: its frame's, else this page's. */
  function doc() {
    try {
      const inner = document.querySelector(SEL.FRAME)?.contentDocument;
      if (inner?.body && inner.location.href !== "about:blank") return inner;
    } catch {}
    return document;
  }
  const all = (selector, root = doc()) => [...root.querySelectorAll(selector)];

  function rows() {
    return all(SEL.ROW).filter((r) => shows(r) && !r.parentElement?.closest(SEL.ROW)
      && !r.closest(SEL.NOT_FIELDS)
      && !r.querySelector("input[type=password]") && !r.closest(SEL.EMAIL_FORM));
  }

  /** Whether the candidate's sign-in shows: the student's. */
  const onGate = () => all(SEL.SIGN_IN).some(shows) && !rows().length;

  /** The step shown, as the engine names it (its icims.ts stepName). "" on the sign-in or the job's page. */
  function icimsStep() {
    if (onGate()) return "";
    const d = doc();
    const current = all(SEL.STEPS).find((li) => li.classList.contains(SEL.STEP_CURRENT) || PAT.CURRENT_STEP.test(li.getAttribute("title") ?? ""));
    const named = oneLine(current?.querySelector(SEL.STEP_CONTENT)?.getAttribute("title") ?? "") || text(current?.querySelector(SEL.STEP_CONTENT) ?? current)
      || text(d.querySelector(SEL.PAGE_STEP));
    const clean = named.replace(PAT.STEP_NUMBER, "").replace(PAT.STEP_STATE, "");
    if (clean) return clean;
    if (!rows().length && !all(SEL.PRIMARY).some(shows)) return "";
    return text(d.querySelector(SEL.HEADER)) || "Application";
  }

  const stepId = () => `${icimsStep()}#${doc().location?.pathname ?? ""}`;
  let lastId = "";

  /** Resolves with the step once it shows and isn't `from` (or is a new page of the same name). Never times out. */
  function stepAfter(from) {
    const fromId = from ? lastId : "";
    return new Promise((resolve) => {
      const check = () => {
        const step = doc().readyState === "complete" ? icimsStep() : "";
        if (!step || (step === from && stepId() === fromId)) return;
        clearInterval(timer);
        lastId = stepId();
        resolve(step);
      };
      const timer = setInterval(check, STEP_LOOK);
      check();
    });
  }

  /** Resolves once the step has stopped changing (STEP_QUIET), at most STEP_QUIET_MAX. */
  function quiet() {
    return new Promise((resolve) => {
      let changed = Date.now();
      const started = Date.now();
      const page = doc();
      const observer = new MutationObserver(() => (changed = Date.now()));
      observer.observe(page.documentElement, { childList: true, subtree: true });
      const timer = setInterval(() => {
        const now = Date.now();
        if (doc() !== page) changed = now; // a new page came in the frame
        if (now - changed < STEP_QUIET && now - started < STEP_QUIET_MAX) return;
        clearInterval(timer);
        observer.disconnect();
        resolve();
      }, 100);
    });
  }

  /** Whether this tab filled the step shown before (the student went back to it), and marks it filled. */
  function filledBefore() {
    const key = stepId();
    let filled = [];
    try { filled = JSON.parse(sessionStorage.getItem(FILLED_STEPS) ?? "[]"); } catch {}
    if (filled.includes(key)) return true;
    try { sessionStorage.setItem(FILLED_STEPS, JSON.stringify([...filled, key])); } catch {}
    return false;
  }

  const GATE_REASON = "Sign in on iCIMS's page: enter your email, answer its privacy notice yourself, then your password (or make your login). WorkIt never types into it. It fills each step once it shows.";

  /** Tells the student, while the sign-in shows, that it is theirs: `onView(reason)` each time it shows. Stops once a step shows. */
  function watchGate(onView) {
    let shown = false;
    const timer = setInterval(() => {
      if (icimsStep()) { clearInterval(timer); return; }
      if (onGate() && !shown) {
        shown = true;
        onView(GATE_REASON);
      }
      if (!onGate()) shown = false;
    }, STEP_LOOK);
  }

  /** A row's label, as the engine reads it (its icims.ts labelOf). */
  function labelOf(row) {
    const ids = new Set(all("input[type=radio], input[type=checkbox]", row).map((i) => i.id).filter(Boolean));
    const own = all(SEL.LABEL, row)
      .find((l) => !(l.htmlFor && ids.has(l.htmlFor)) && !l.querySelector("input[type=radio], input[type=checkbox]") && text(l));
    if (own) return text(own);
    return all("input[type=checkbox]", row).length === 1 ? text(row.querySelector("label")) : "";
  }

  /** The field on the step shown for a panel row's key, "<step> / <label>" (a repeated one numbered, "Phone (2)"); null for another step's. */
  function fieldOf(key) {
    const step = icimsStep();
    if (!step || !key.startsWith(`${step} / `)) return null;
    const name = key.slice(step.length + 3);
    const seen = {};
    for (const row of rows()) {
      const label = labelOf(row);
      if (!label) continue;
      seen[label] = (seen[label] ?? 0) + 1;
      if (name === label + (seen[label] > 1 ? ` (${seen[label]})` : "")) return row;
    }
    return null;
  }

  window.WIA.icims = {
    isOn,
    site: "icims",
    name: "iCIMS",
    doc,
    step: icimsStep,
    stepId,
    fieldOf,
    stepAfter,
    quiet,
    filledBefore,
    watchGate,
    // The words the panel uses before the steps, on the sign-in, and for the step's own button.
    waiting: { title: "Sign in to iCIMS, then WorkIt fills", reason: "Start the application on iCIMS's page and sign in there. WorkIt never types into it, and fills each step once it shows." },
    gateFirst: "Sign in on iCIMS's page first. ",
    nextLabel: "Next",
    reviewName: "last",
    // Fill to Review's view of the page (workday-walk.js), in the frame (`doc`), read at each use.
    walk: {
      get next() { return SEL.PRIMARY; },
      get review() { return SEL.SUBMIT; },
      get goesOn() { return PAT.GOES_ON; },
      get banner() { return SEL.ERROR_BANNER; },
      wentWrong: () => false,
    },
  };
})();
