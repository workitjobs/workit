"""Approve and submit (ADR 0006): the held form's own Submit, which Apply presses once the student approves it.

The page is the student's by then (the submit guard is off), so the press is the one they would make. Apply presses
only a button it is sure of: exactly one visible button, in the page or any of its frames, whose words send the
application (rehearsal.FINAL: Submit, Send), never one that names a code (Send New Code). None, or more than one, and it presses nothing: the student presses it.
Nor while the form still has a required field blank (BLANK): the job site would turn the press down unsent, and a
Send anyway that pressed it sent a form with a required answer missing (Veeva, live 2026-11-27).
"""

import re

# Marks the one Submit button it found in a frame, then returns the words of every one it saw there.
FIND = r"""() => {
  const words = el => (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
  const shown = el => {
    const box = el.getBoundingClientRect(), style = getComputedStyle(el);
    return box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && !el.disabled
      && el.getAttribute('aria-disabled') !== 'true';
  };
  document.querySelectorAll('[data-apply-send]').forEach(el => el.removeAttribute('data-apply-send'));
  const found = [...document.querySelectorAll('button, input[type=submit], [role=button]')]
    .filter(el => shown(el) && words(el).length <= 40 && /\b(submit|send)\b/i.test(words(el))
      && !/\bcode\b/i.test(words(el)));  // a code step's Send New Code asks for a code and voids the one typed
  if (found.length === 1) found[0].setAttribute('data-apply-send', '');
  return found.map(words);
}"""

# The labels of the required fields left blank in a frame: a visible field of a form the browser checks as it posts
# (Lever's whole-page post) that it reads as missing its value (a box, a list, a radio group, a file), named by its label, its Lever or Greenhouse question's heading, or its
# own name. Each label once.
BLANK = r"""() => {
  const said = (e) => (e && (e.innerText || e.textContent) || '').replace(/\s+/g, ' ').replace(/[✱*]\s*$/, '').trim();
  const shown = (e) => e.type !== 'hidden' && (!e.checkVisibility || e.checkVisibility({visibilityProperty: true})
    || e.type === 'file' || e.type === 'radio' || e.type === 'checkbox');
  const label = (e) => said(e.labels && e.labels[0])
    || said(e.closest('.application-question, li, fieldset, .field')?.querySelector('.application-label, label, legend'))
    || e.getAttribute('aria-label') || e.name || e.id;
  // A checkbox group (Greenhouse's "Preferred office?", each box `required`) is answered when any of its boxes is
  // ticked, and named by its heading, not by a box (SambaNova, 2026-11-27).
  const group = (e) => e.type === 'checkbox' && e.name
    ? [...e.form.elements].filter((o) => o.type === 'checkbox' && o.name === e.name) : [];
  const out = [];
  for (const e of document.querySelectorAll('input[required], select[required], textarea[required]')) {
    if (!e.form || e.form.noValidate || !e.validity || !e.validity.valueMissing || !shown(e)) continue;
    const boxes = group(e);
    if (boxes.some((o) => o.checked)) continue;
    const words = boxes.length > 1
      ? said(e.closest('fieldset')?.querySelector('legend')) || e.getAttribute('description') || e.name : label(e);
    if (words && !out.includes(words)) out.push(words.slice(0, 120));
  }
  return out;
}"""
# A click Apply never made: the button was covered, hidden or disabled the whole time (the plain Worker's and
# Playwright's own retry reasons). A click whose reply was lost may have sent the form; one of these sent nothing.
NEVER_CLICKED = re.compile(r"intercepts pointer events|element is not (visible|enabled)|outside of the viewport|"
                           r"element has no size", re.IGNORECASE)

NONE = "Apply found no Submit button on the form, so it pressed nothing: press Submit on the page yourself."
SEVERAL = "The form shows more than one Submit button ({}), so Apply pressed none: press the right one yourself."


BLANK_REQUIRED = ("The form still has a required field blank ({}), so Apply pressed nothing: fill it in, then press "
                  "Submit yourself.")
COVERED = ("Something on the page kept Apply's press off Submit ({}), so Apply pressed nothing and nothing went in: "
           "close it, then press Submit yourself.")


class NotPressed(Exception):
    """Apply couldn't tell which button sends the form: it pressed nothing, and the student presses it."""


class Unsure(Exception):
    """Apply pressed the one Submit button, but the press never answered: a Submit that sends the page away (Lever's
    is a whole-page post) can end the click before its reply comes back. It may have gone in, so it counts as a press:
    the job system's confirmation is watched, and Apply never presses it again."""

    def __init__(self, words: str):
        super().__init__(words)
        self.words = words


def press(page) -> str:
    """Press the held form's one Submit button; its words. Raises NotPressed when there is none, or more than one,
    and when the form has a required field blank, or the click never reached the button; Unsure when the click was
    sent but never answered."""
    found = []
    for frame in page.frames:
        try:
            words = frame.evaluate(FIND)
        except Exception:
            continue  # a frame gone, or one Apply can't read: no button of its can be pressed
        found += [(frame, w) for w in words or ()]
    if not found:
        raise NotPressed(NONE)
    if len(found) > 1:
        raise NotPressed(SEVERAL.format(", ".join(f"'{w}'" for _, w in found)))
    frame, words = found[0]
    if blank := blank_required(page):
        raise NotPressed(BLANK_REQUIRED.format(", ".join(f"'{label}'" for label in blank)))
    try:
        frame.locator("[data-apply-send]").click(timeout=10_000)
    except Exception as lost:
        if never := NEVER_CLICKED.search(str(lost)):
            raise NotPressed(COVERED.format(_cover(str(lost)) or never[0])) from lost
        raise Unsure(words) from lost
    return words


def blank_required(page) -> list[str]:
    """The labels of the required fields the form still leaves blank, in every frame it can read (BLANK)."""
    blank: list[str] = []
    for frame in page.frames:
        try:
            blank += [str(label) for label in frame.evaluate(BLANK) or () if str(label) not in blank]
        except Exception:
            continue  # a frame gone, or one Apply can't read
    return blank


def _cover(error: str) -> str:
    """What covered the button, as the click's retry named it ("<div id=onetrust-banner-sdk>"), else ""."""
    found = re.search(r"(<[^</>][^<>]{0,80}>)(?:[^<]{0,80}</\w+>)? intercepts pointer events", error)
    return found[1] if found else ""
