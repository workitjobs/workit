// Check before Submit (KAN-747): the extension's copy of Apply's Pre-submit
// check (apply-agent/docs/held-forms.md, "Verifying a filled form"), with
// the student as the checker. A view of the panel (panel.js's "check" slot)
// that lists every answer this fill filled or wrote on the page, flagged
// ones first: what still needs the student (a required field still empty, a
// failed field, an answer the page shows otherwise, an answer the review
// flagged), then WorkIt's guesses, then the answers their Claude wrote, then
// what waits on their Claude, then the rest as filled. Each row shows the
// answer as the engine read it back and goes to its field when pressed
// (batch-tab.js's showField). Review and submit opens it (primary.js), and
// the ⋯ menu's Check before Submit at any time after a fill. It only reads:
// it never types, picks or presses the employer's Submit. Loaded before
// primary.js (shared/content-scripts.js), as window.WIA.presubmit.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  // Injected again (Fill Again): the last fill's view goes.
  window.WIA.presubmit?.unmount?.();

  // An answer never shown in the panel: the field holds a secret.
  const SECRET = /password|passcode|social security|\bssn\b/i;
  const PREVIEW = 120;

  const CSS = `
    [data-slot="check"] { padding: 12px 0 4px; }
    [data-slot="check"] h2 { margin: 0 12px 2px; font-size: var(--text-label); font-weight: 600; }
    [data-slot="check"] .check-lead { margin: 0 12px 8px; font-size: var(--text-note); color: var(--color-ink-meta); }
    [data-slot="check"] .check-head { margin: 8px 12px 2px; font-size: var(--text-meta); font-weight: 600; color: var(--color-ink-meta); }
    [data-slot="check"] .row { cursor: pointer; }
    [data-slot="check"] .row:hover .label { text-decoration: underline; }
    [data-slot="check"] .row:focus-visible { outline: 2px solid var(--color-brand); outline-offset: -2px; }
    [data-slot="check"] .check-why { font-size: var(--text-note); margin-top: 2px; color: var(--color-warning-strong); }
    [data-slot="check"] .row[data-mark="needs-you"] .check-why { color: var(--color-danger); }
    [data-slot="check"] .check-answer { font-size: var(--text-note); color: var(--color-ink-muted); margin-top: 2px; overflow-wrap: anywhere; }
    [data-slot="check"] .check-back { all: unset; cursor: pointer; margin: 8px 12px; padding: 4px 10px; font-size: var(--text-note); font-weight: 500;
      border: 1px solid var(--color-border-subtle); border-radius: var(--radius-control); }
    [data-slot="check"] .check-back:focus-visible { outline: 2px solid var(--color-brand); outline-offset: 2px; }
  `;

  let style = null;
  let unsubscribe = null;
  let shown = false;

  const isEmpty = (v) => v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

  /**
   * Why a row is flagged, as `{ tier, mark, why }`, or null for an answer
   * that asks nothing of the student. Tier orders the list: 0 needs you,
   * 1 WorkIt's guess, 2 Claude's words, 3 waiting on Claude.
   */
  function flagOf(r) {
    const status = window.WIA.status;
    if (status.needsYou(r)) {
      if (r.flag) return { tier: 0, mark: "needs-you", why: `Your Claude's check: ${r.flag}` };
      if (r.status === "failed") return { tier: 0, mark: "needs-you", why: isEmpty(r.shows) ? (r.required ? "Required, and still empty." : "Empty on the page.") : "The page shows something other than WorkIt's answer." };
      return { tier: 0, mark: "needs-you", why: "Required, and still empty." };
    }
    if (r.status === "filled" && r.source === "guessed") return { tier: 1, mark: "check", why: "WorkIt guessed this. Check it is true for you." };
    if (r.status === "filled" && r.source === "claude") return { tier: 2, mark: "check", why: "Your Claude wrote this. Read it before you submit." };
    // A written answer that isn't the student's typing on this page: pasted in, or a saved answer filled in words.
    const written = window.WIA.writtenRow?.has(r.key);
    if (r.status === "filled" && r.source === "pasted") return { tier: 2, mark: "check", why: "Pasted in. Read it before you submit." };
    if (r.status === "filled" && r.source === "saved" && written) return { tier: 2, mark: "check", why: "A saved answer. Check it fits this job." };
    if (status.toCheck(r)) return { tier: 2, mark: "check", why: "A new answer. Read it before you submit." };
    if (status.waitingOnClaude(r)) return { tier: 3, mark: "waiting", why: "Waiting for your Claude to write it." };
    return null;
  }

  /**
   * The list: every field the fill filled or wrote, and every one still
   * needing the student, flagged first (by tier), each part in page order.
   * Notes, optional fields left empty and questions the form isn't asking
   * now are not answers, so they are left out.
   */
  function items() {
    const fields = (window.WIA.status?.summary().fields ?? []).filter((r) => !r.note);
    const listed = fields
      .map((r) => ({ r, flag: flagOf(r) }))
      .filter(({ r, flag }) => flag || r.status === "filled");
    const ordered = window.WIA.groups?.inPageOrder ? window.WIA.groups.inPageOrder(listed, (i) => [i.r.key]) : listed;
    // A stable sort: page order holds inside each tier.
    return ordered.sort((a, b) => (a.flag?.tier ?? 9) - (b.flag?.tier ?? 9));
  }

  /** The answer as the engine read it back, on one short line; a secret's is never shown. */
  function answerText(r) {
    if (isEmpty(r.shows)) return "";
    if (SECRET.test(r.label ?? "") || SECRET.test(r.key)) return "(hidden)";
    const text = (Array.isArray(r.shows) ? r.shows.join(", ") : String(r.shows)).replace(/\s+/g, " ").trim();
    return text.length > PREVIEW ? `${text.slice(0, PREVIEW - 1)}…` : text;
  }

  function row({ r, flag }) {
    const { el } = window.WIA.ui;
    const node = el("div", "row");
    node.dataset.key = r.key;
    node.dataset.open = "";
    node.dataset.mark = flag?.mark ?? "filled";
    if (flag) node.dataset.flagged = String(flag.tier);
    node.tabIndex = 0;
    node.setAttribute("role", "link");
    node.title = "Go to this field";
    const text = el("div", "text");
    text.append(el("div", "label", r.label + (r.required ? "" : " (optional)")));
    if (flag) text.append(el("div", "check-why", flag.why));
    const answer = answerText(r);
    if (answer) text.append(el("div", "check-answer", answer));
    const sourceLabel = window.WIA.overlay?.SOURCE_LABEL?.[r.source];
    if (r.status === "filled" && sourceLabel) {
      const source = el("span", "source", sourceLabel);
      source.dataset.source = r.source;
      text.append(source);
    }
    node.append(el("span", "dot"), text);
    return node;
  }

  /** Goes to a row's field: scrolled to, focused and ringed. A field the page doesn't show gets a line saying so. */
  function go(event) {
    if (event.type === "keydown" && event.key !== "Enter") return;
    const node = event.target.closest(".row[data-key]");
    if (!node) return;
    const key = node.dataset.key;
    if (window.WIA.showField?.(key)) return;
    // On Workday, a field of another step names its step, as a checklist row does (overlay.js jump).
    const step = key.split(" / ")[0];
    const steps = window.WIA.steps;
    const elsewhere = steps && key.includes(" / ") && step !== steps.step?.();
    const said = window.WIA.ui.el("div", "reason note", elsewhere ? `This is on ${steps.name}'s ${step} step.` : "WorkIt can't find this field on the page.");
    node.querySelector(".text").append(said);
    setTimeout(() => said.remove(), 4000);
  }

  function render() {
    const view = window.WIA.panel?.slot("check");
    if (!view || !shown) return;
    const list = items();
    const flagged = list.filter((i) => i.flag).length;
    const { el } = window.WIA.ui;
    const head = el("h2", null, "Check before Submit");
    const lead = el(
      "p",
      "check-lead",
      `${list.length} ${list.length === 1 ? "answer" : "answers"} on this page · ${flagged ? `${flagged} to check first` : "none flagged"}. WorkIt never presses Submit: you do.`,
    );
    const parts = [head, lead];
    if (flagged) parts.push(el("div", "check-head", "Check these first"), ...list.filter((i) => i.flag).map(row));
    if (list.length > flagged) parts.push(el("div", "check-head", "Filled"), ...list.filter((i) => !i.flag).map(row));
    const back = window.WIA.ui.button("Back", () => close());
    back.className = "check-back";
    parts.push(back);
    // A redraw keeps the row a keyboard user is on focused.
    const focusedKey = window.WIA.panel.root.activeElement?.closest?.('[data-slot="check"] .row[data-key]')?.dataset.key;
    view.replaceChildren(...parts);
    if (focusedKey) view.querySelector(`.row[data-key="${CSS.escape(focusedKey)}"]`)?.focus({ preventScroll: true });
  }

  /** Shows the view in place of the Autofill tab's body. */
  function open() {
    const panel = window.WIA.panel;
    if (!panel?.slot("check")) return false;
    shown = true;
    render();
    panel.showView("check", true);
    return true;
  }

  function close() {
    if (!shown) return;
    shown = false;
    window.WIA.panel?.showView("check", false);
  }

  /** A view showed or went (panel.onView): whether this one shows now, and the button's words with it (primary.js). */
  function viewed(name, on) {
    shown = name === "check" && on;
    window.WIA.primary?.refresh();
  }

  const isOpen = () => shown;

  /** Readies the view for the fill that just mounted its rows (primary.js's mount). */
  function mount() {
    const panel = window.WIA.panel;
    const view = panel?.slot("check");
    if (!view || style) return;
    style = panel.addCss(CSS);
    // The view outlives a fill (it is the shell's): its presses are heard once per page.
    if (!view.dataset.heard) {
      view.dataset.heard = "";
      view.addEventListener("click", window.WIA.ui.trusted((event) => window.WIA.presubmit.go(event)));
      view.addEventListener("keydown", window.WIA.ui.trusted((event) => window.WIA.presubmit.go(event)));
      // Another view, or a tab's press, leaves this one (showView hides every view but the one it shows).
      panel.onView((name, on) => window.WIA.presubmit?.viewed(name, on));
    }
    unsubscribe = window.WIA.status.subscribe(render);
    panel.menuItem("check", { label: "Check before Submit", order: 35, onPress: () => (shown ? close() : open()) });
  }

  function unmount() {
    close();
    unsubscribe?.();
    unsubscribe = null;
    style?.remove();
    style = null;
    window.WIA.panel?.menuItem?.("check", null);
    window.WIA.panel?.slot("check")?.replaceChildren();
  }

  window.WIA.presubmit = { mount, unmount, open, isOpen, go, viewed };
})();
