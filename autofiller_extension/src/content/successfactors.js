// SAP SuccessFactors' career site, for the fill (content-script.js): which
// page shows, when it has settled, and its sign-in. The sign-in and its
// Create an Account page are the student's: WorkIt never types an email or a
// password there, never makes an account, and never presses their buttons.
// The panel tells the student to sign in; the application fills once it
// shows. Signed in, the application is one page of sections ("Application")
// and, at some employers, a page of screening questions ("Questions"), as
// the engine's successfactors.ts names them. The same face as workday.js
// gives (see steps.js); loaded after oracle.js, as window.WIA.successfactors.
// Its selectors and patterns are the Rules table's (site-data.js: SEL, PAT), read at each use.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  const { SEL, PAT } = window.WIA.site("successfactors");
  // How long a page must stop changing before it is read, and the longest wait for that.
  const STEP_QUIET = 600;
  const STEP_QUIET_MAX = 10_000;
  const FILLED_STEPS = "workit-successfactors-filled";
  const oneLine = (text) => String(text ?? "").replace(/\s+/g, " ").trim();
  const shows = (el) => Boolean(el) && el.getClientRects().length > 0;
  const text = (el) => (el ? oneLine(el.innerText ?? el.textContent).replace(/^\*\s*|\s*\*$/g, "").replace(/\s*:$/, "") : "");

  const isOn = /(^|\.)(successfactors|sapsf)\.(com|eu)$/.test(location.hostname) && /^\/(career|careers|portalcareer)\/?$/.test(location.pathname);

  /** Whether the sign-in (or its Create an Account page) shows: the student's. */
  const onGate = () => [...document.querySelectorAll(SEL.GATE)].some(shows);

  /** The page's field rows, as the engine reads them (its successfactors.ts rows). */
  function rows() {
    return [...document.querySelectorAll(SEL.ROW)].filter((r) => shows(r)
      && !r.parentElement?.closest(SEL.ROW)
      && !PAT.ENTRIES.test(text(r.closest(SEL.SECTION)?.querySelector(SEL.SECTION_TITLE)))
      && (r.tagName !== "TR" || r.children.length >= 2));
  }

  /** The page shown, as the engine names it: "Questions" or "Application". "" on the sign-in or any other page. */
  function sfStep() {
    if (onGate()) return "";
    const footer = [...document.querySelectorAll(`${SEL.NEXT}, ${SEL.SEND_BUTTONS}`)].some(shows);
    if (!rows().length && !footer) return "";
    return [...document.querySelectorAll(SEL.QUESTIONS_PAGE)].some(shows) ? "Questions" : "Application";
  }

  const stepId = () => `${sfStep()}#${rows().map(labelOf).join("|").length}`;

  /** Resolves with the page once it shows and isn't `from`. Watches the page; never times out. */
  function stepAfter(from) {
    const fromId = from ? lastId : "";
    return new Promise((resolve) => {
      const check = () => {
        const step = sfStep();
        if (!step || (step === from && stepId() === fromId)) return false;
        observer.disconnect();
        lastId = stepId();
        resolve(step);
        return true;
      };
      const observer = new MutationObserver(check);
      if (!check()) observer.observe(document.documentElement, { childList: true, subtree: true });
    });
  }
  let lastId = "";

  /** Resolves once the page has stopped changing (STEP_QUIET), at most STEP_QUIET_MAX. */
  function quiet() {
    return new Promise((resolve) => {
      let timer;
      const done = () => { observer.disconnect(); clearTimeout(timer); clearTimeout(limit); resolve(); };
      const observer = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(done, STEP_QUIET); });
      observer.observe(document.documentElement, { childList: true, subtree: true });
      timer = setTimeout(done, STEP_QUIET);
      const limit = setTimeout(done, STEP_QUIET_MAX);
    });
  }

  /** Whether this tab filled the page shown before (the student went back to it), and marks it filled. */
  function filledBefore() {
    const req = new URLSearchParams(location.search).get("career_job_req_id") ?? document.querySelector("#career_job_req_id")?.value ?? "";
    const key = `${req} ${sfStep()}`;
    let filled = [];
    try { filled = JSON.parse(sessionStorage.getItem(FILLED_STEPS) ?? "[]"); } catch {}
    if (filled.includes(key)) return true;
    try { sessionStorage.setItem(FILLED_STEPS, JSON.stringify([...filled, key])); } catch {}
    return false;
  }

  /** Tells the student, while the sign-in shows, that it is theirs: `onView(reason)` each time it shows. Nothing on it is typed or pressed. */
  function watchGate(onView) {
    let shown = false;
    const look = () => {
      if (sfStep()) { observer.disconnect(); return; }
      if (onGate() && !shown) {
        shown = true;
        onView(GATE_REASON);
      }
      if (!onGate()) shown = false;
    };
    const observer = new MutationObserver(look);
    observer.observe(document.documentElement, { childList: true, subtree: true });
    look();
  }

  /** A row's label, as the engine reads it (its successfactors.ts labelOf). */
  function labelOf(row) {
    const own = row.querySelector(SEL.LABEL);
    return text(own) || text(row.querySelector("label"));
  }

  /** The field on the page shown for a panel row's key, "<step> / <label>" (a repeated one numbered, "Phone (2)"); null for another page's. */
  function fieldOf(key) {
    const step = sfStep();
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

  const GATE_REASON = "Sign in to SuccessFactors on this page (or create your account there), then press Fill. WorkIt never signs in, types a password or makes an account for you. It fills the application once it shows.";

  window.WIA.successfactors = {
    isOn,
    site: "successfactors",
    name: "SuccessFactors",
    step: sfStep,
    stepId,
    fieldOf,
    stepAfter,
    quiet,
    filledBefore,
    watchGate,
    // The words the panel uses before the application, and for the page's own button.
    waiting: { title: "Sign in to SuccessFactors, then press Fill", reason: GATE_REASON },
    nextLabel: "Next",
    reviewName: "Apply",
    // Fill to Review's view of the page (workday-walk.js), read at each use.
    walk: {
      get next() { return SEL.NEXT; },
      get review() { return SEL.SEND_BUTTONS; },
      get goesOn() { return PAT.GOES_ON; },
      get banner() { return SEL.ERROR_BANNER; },
      wentWrong: () => false,
    },
  };
})();
