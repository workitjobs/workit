// The coverage badge (KAN-749), in the shell's "coverage" slot under the job
// card, before a fill: whether WorkIt fully supports this site, partly
// supports it (a job system whose form comes in steps) or doesn't support it
// (background/coverage.js, from the Fill engine's job system for the page).
// On a site it doesn't support, the Autofill tab lists the student's answers
// (panel/answers), each with Copy, so they can fill the form by hand. A
// fill's list (overlay.js draw) takes the tab, and the badge goes.
//
// `show()` is what panel-states.js's start() calls before a fill, and what
// the popup's Show My Answers runs on a site WorkIt can't fill (background.js
// openAnswers). Loaded after report.js wherever the panel is (SHELL_FILES,
// CONTENT_SCRIPT_FILES); the first copy stays.
window.WIA = window.WIA || {};

(function () {
  "use strict";

  if (window.WIA.coverage) return;
  const { send, el, button } = window.WIA.ui;

  const STYLES = `
    [data-slot="coverage"] { padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
    .coverage-badge {
      align-self: flex-start; font-size: var(--text-meta); line-height: var(--text-meta--line-height); font-weight: 600;
      padding: 1px 8px; border-radius: 9999px;
    }
    .coverage-badge[data-level="full"] { background: var(--color-positive-tint); color: var(--color-positive-ink); }
    .coverage-badge[data-level="partial"] { background: var(--color-warning-tint); color: var(--color-warning); }
    .coverage-badge[data-level="none"] { background: var(--color-well); color: var(--color-ink-meta); }
    .coverage-said { font-size: var(--text-note); line-height: var(--text-note--line-height); color: var(--color-ink-muted); }
    .answers { display: flex; flex-direction: column; gap: 12px; padding: 12px; }
    .answers h3 { margin: 0 0 4px; font-size: var(--text-note); font-weight: 600; color: var(--color-ink-meta); }
    .answers .answer { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid var(--color-border-subtle); }
    .answers .answer:first-of-type { border-top: none; }
    .answers .answer-text { flex: 1; min-width: 0; }
    .answers .answer-label { font-size: var(--text-meta); color: var(--color-ink-meta); }
    .answers .answer-value { font-size: var(--text-note); color: var(--color-ink); overflow-wrap: anywhere; }
    .answers button {
      all: unset; flex: none; cursor: pointer; padding: 4px 10px; font-size: var(--text-note); font-weight: 600; border-radius: var(--radius-control);
      border: 1px solid var(--color-border-subtle); background: var(--color-panel); color: var(--color-ink);
    }
    .answers button:hover { background: var(--color-hover); }
    .answers button:focus-visible { outline: 2px solid var(--color-brand); outline-offset: 2px; }
    .answers .answers-said { font-size: var(--text-note); color: var(--color-ink-muted); }
    .answers .answers-said[data-error] { color: var(--color-danger); }
  `;

  let styled = false;
  const panel = () => window.WIA.panel;
  function style() {
    if (styled || !panel()?.root) return;
    styled = true;
    panel().addCss(STYLES);
  }

  /** Copies `text` to the student's clipboard (letter-preview.js's way, with its fallback). */
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const box = Object.assign(document.createElement("textarea"), { value: text });
      document.body.append(box);
      box.select();
      document.execCommand("copy");
      box.remove();
    }
  }

  /** The badge for this page, and on a site WorkIt can't fill, the answers to copy. */
  async function show() {
    style();
    const place = panel()?.slot("coverage");
    if (!place) return;
    const answer = await send({ type: "panel/coverage" });
    if (!answer?.ok) return;
    const badge = el("span", "coverage-badge", answer.badge);
    badge.dataset.level = answer.level;
    place.replaceChildren(badge, el("div", "coverage-said", answer.said));
    place.dataset.level = answer.level;
    place.hidden = false;
    if (answer.level === "none") await showAnswers();
  }

  /** The student's answers in the Autofill tab, by group, each with Copy (Copied once pressed). */
  async function showAnswers() {
    const tab = panel().slot("tab:autofill");
    if (!tab) return;
    const list = el("div", "answers");
    list.dataset.answers = "";
    tab.replaceChildren(list);
    const answer = await send({ type: "panel/answers" });
    if (!answer?.ok) {
      const said = el("div", "answers-said", "WorkIt couldn't load your answers. ");
      said.dataset.error = "";
      said.append(button("Try again", () => void showAnswers()));
      return list.replaceChildren(said);
    }
    if (!answer.answers.length) return list.replaceChildren(el("div", "answers-said", "WorkIt has no answers to copy yet. Add them in My Profile on WorkIt."));
    const groups = new Map();
    for (const row of answer.answers) {
      if (!groups.has(row.group)) {
        const section = el("section");
        section.append(el("h3", null, row.group));
        groups.set(row.group, section);
        list.append(section);
      }
      const line = el("div", "answer");
      const words = el("div", "answer-text");
      words.append(el("div", "answer-label", row.label), el("div", "answer-value", row.value));
      const press = button("Copy", async () => {
        await copy(row.value);
        for (const other of list.querySelectorAll("button[data-copied]")) {
          other.textContent = "Copy";
          other.setAttribute("aria-label", `Copy ${other.dataset.copied}`);
          delete other.dataset.copied;
        }
        press.textContent = "Copied";
        press.setAttribute("aria-label", `Copied ${row.label}`);
        press.dataset.copied = row.label;
      });
      press.setAttribute("aria-label", `Copy ${row.label}`);
      line.append(words, press);
      groups.get(row.group).append(line);
    }
  }

  /** A fill took the panel (overlay.js): the badge goes. */
  function hide() {
    const place = panel()?.slot("coverage");
    if (place) place.hidden = true;
  }

  window.WIA.coverage = { show, hide };
})();
