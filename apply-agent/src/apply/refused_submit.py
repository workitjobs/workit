"""Why a Submit Apply pressed didn't go in, as the form says it (Approve and submit, ADR 0006).

Greenhouse, Ashby and Lever check the form in the page before anything is sent: a required box left unticked, or a
field React emptied, keeps the form where it is under a red message ("Please accept the terms to proceed.", Epic
Games' and ENFOS's demographic consent, live 2026-11-26), and no application or email follows. Apply then waited
out its two minutes and handed the form over with nothing to say but that it may have gone in.

`errors(page)` reads each such message with the form field it is about. The hold (rehearsal) fixes those fields once
from the Plan, presses Submit once more, and hands the form over only when the page still refuses it, with the
page's own words. A field message proves nothing was sent, which is why that one press more is safe; a captcha is
never touched, and a code step is asked for, not read here.
"""

import re
from dataclasses import dataclass

from apply import captcha, upload_origin
from apply.model import Question

# Each visible field error, with the ids and name of the control it is about: a field marked aria-invalid with its
# aria-errormessage or aria-describedby text, then role=alert and any element whose class says error (Greenhouse's
# helper-text--error, Lever's error-message, Ashby's _error_ classes), its control the one in the nearest block
# around it that holds one. The ids are the control's and each of its blocks', so a box whose own id is
# `<name>_1` (Greenhouse's lone consent box) is still known by its question's name. Apply's own notes (id apply-*)
# are no errors, nor a block that holds a control (a whole section, not its message).
ERRORS = r"""() => {
  const said = (e) => (e && e.innerText || '').replace(/\s+/g, ' ').trim();
  const shown = (e) => { const box = e.getBoundingClientRect(), style = getComputedStyle(e);
    return box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && style.display !== 'none'; };
  const ok = (e) => e && !e.closest('[id^="apply-"]') && shown(e) && !e.querySelector('input, select, textarea')
    && said(e) && said(e).length <= 300;
  const CONTROL = 'input:not([type=hidden]), select, textarea';
  const names = (control) => {
    if (!control) return [];
    const found = [control.getAttribute('name') || ''];
    for (let p = control; p && p !== document.body; p = p.parentElement) if (p.id) found.push(p.id);
    return found.filter(Boolean);
  };
  const near = (e) => {
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const control = p.querySelector(CONTROL);
      if (control) return control;
    }
    return null;
  };
  const out = [], seen = new Set();
  const add = (e, control) => {
    if (!ok(e) || seen.has(e)) return;
    seen.add(e);
    out.push({words: said(e), names: names(control)});
  };
  for (const field of document.querySelectorAll('[aria-invalid=true]')) {
    const ids = (field.getAttribute('aria-errormessage') || field.getAttribute('aria-describedby') || '').split(/\s+/);
    for (const id of ids) if (id) add(document.getElementById(id), field);
  }
  for (const e of document.querySelectorAll('[role=alert], [class*=error i]')) add(e, near(e));
  return out;
}"""


@dataclass(frozen=True)
class FieldError:
    words: str  # the message, as the page shows it
    names: tuple[str, ...] = ()  # the name and ids of the control it is about, none for a message on the whole form

    def about(self, question: Question) -> bool:
        return question.name in self.names


def errors(page) -> list[FieldError]:
    """Each field error the page shows, in its frames of the form's own site; none for a page that can't be read.
    Never a captcha's frame: what it says is the captcha's, and Apply never touches one."""
    found: list[FieldError] = []
    for n, frame in enumerate(page.frames):
        if n and (captcha.in_frame(frame.url) or not upload_origin.frame_may_upload(frame)):
            continue
        try:
            said = frame.evaluate(ERRORS) or []
        except Exception:
            continue  # a frame gone or going
        found += [FieldError(str(e.get("words", "")), tuple(map(str, e.get("names") or ()))) for e in said]
    return [e for i, e in enumerate(found) if e.words and e.words not in {f.words for f in found[:i]}]


def words(found: list[FieldError]) -> str:
    """The page's messages, as a card quotes them."""
    return " ".join(f"'{e.words.rstrip()}'" for e in found)


def fixable(found: list[FieldError], questions: tuple[Question, ...] | list[Question]) -> list[Question]:
    """The questions the messages are about, when every message is about one the form asked; none when any is
    not (a message on the whole form, a field Apply never read): that one is the student's."""
    about = [[q for q in questions if e.about(q)] for e in found]
    if not found or not all(about):
        return []
    return list({q.name: q for qs in about for q in qs}.values())


# A job site's own word that it refused the whole send: a toast or banner, in any markup, on no field. Workable's
# "Something went wrong. We are working on this, please try again later." after Apply's press (Digital Control,
# Infleqtion, live 2026-11-27) came with no confirmation and no email, and went within seconds.
SITE_ERROR = re.compile(r"something went wrong|(please )?try again later|an? (unexpected |unknown |internal )?error "
                        r"(has )?occurred|(could ?n[o'’]t|unable to|failed to) (submit|send|process|save) (your |the |this )?"
                        r"(application|form|submission)|submission failed"
                        # Oracle's, once another tab signed in to its site (Honeywell, live 2026-11-27): "Your
                        # application couldn't be submitted. You already created your profile in another browser tab."
                        r"|(application|form|submission) (could|can|was|has) ?(n[o'’]t|not) (be|been) (submitted|sent)"
                        r"|in another (browser )?tab", re.IGNORECASE)
# The site's refusal because another tab of the same site signed in since (OTHER_TAB_REFUSED).
OTHER_TAB = re.compile(r"in another (browser )?tab", re.IGNORECASE)
# Each line of the page's text, Apply's own notes (id apply-*) left out.
LINES = r"""() => {
  const own = new Set();
  for (const e of document.querySelectorAll('[id^="apply-"]'))
    for (const line of (e.innerText || '').split('\n')) own.add(line.trim());
  return ((document.body && document.body.innerText) || '').split('\n').map((line) => line.trim())
    .filter((line) => line && line.length <= 300 && !own.has(line));
}"""


def site_errors(page) -> dict[str, None]:
    """Each line the page shows now that says the site refused a send (SITE_ERROR), in page order, in the frames of
    the form's own site; none for a page that can't be read. Never a captcha's frame."""
    found: dict[str, None] = {}
    for n, frame in enumerate(page.frames):
        if n and (captcha.in_frame(frame.url) or not upload_origin.frame_may_upload(frame)):
            continue
        try:
            found |= {line: None for line in frame.evaluate(LINES) or [] if SITE_ERROR.search(line)}
        except Exception:
            continue  # a frame gone or going
    return found


def new_site_error(page, before) -> str:
    """The site's refusal that came after Apply's press, as the page words it, each of its lines in page order
    (`before`: site_errors at the press, so a question or text already on the form never counts); "" for none."""
    return " ".join(line for line in site_errors(page) if line not in before)
