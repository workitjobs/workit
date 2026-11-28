"""What a held form shows when it is sent (W11): the values WorkIt keeps as what the application sent.

The Record holds each answer as the fill read it back, and the student can change a field on the held form before
they send it. So on each turn of the held page (rehearsal's `tend`) a listener goes into each frame's document that
lacks one. On a press of a button there (Submit, Next, Save and Continue), before the page's own handlers run, it reads
every question's field as Needs you on the page reads one (`on_page.FIELD`, which reads a custom list's picked option
too) and hands the values to Apply. Each press keeps what that page shows then, so a form of many steps keeps each step
as the student left it, and its Submit the last page's. Approve and submit reads the form the same way just before
Apply presses (`read_now`): a plain Worker's press is the worker extension's, which a page listener may not hear.

It only reads: it never prevents, delays or changes a press, needs no guard and no Worker extension change, and a
read that fails sends nothing (the Record's value stands). A page's own script could call its binding with values of
its own: that changes only the student's record of what was sent, never what is submitted."""

import json

from apply.model import Question
from apply.on_page import FIELD

BINDING = "__applySentFields"

# Put into each frame on each turn: the listener is made once a window and added again each time (the same function
# twice is one listener), so one a document.open() erased comes back, and the questions are renewed.
LISTEN = """(questions) => {
  window.__applySentQuestions = questions;
  if (!window.__applySentListener) {
    const field = @FIELD@;
    window.__applySentListener = (event) => {
      try {
        const at = event.target && event.target.closest
          && event.target.closest('button, input[type=submit], input[type=button], [role=button], a');
        const tell = window.@BINDING@;
        if (!at || typeof tell !== 'function') return;
        const seen = [];
        for (const [name, label] of window.__applySentQuestions || []) {
          try { const got = field([name, label, 'read', 0]); if (got && got.found) seen.push([name, got.value || '']); }
          catch (e) {}
        }
        if (seen.length) tell(JSON.stringify(seen));
      } catch (e) {}
    };
  }
  addEventListener('click', window.__applySentListener, true);
}""".replace("@FIELD@", FIELD).replace("@BINDING@", BINDING)

# The same read, now, for Approve and submit.
READ = """(questions) => {
  const field = @FIELD@;
  const seen = [];
  for (const [name, label] of questions) {
    try { const got = field([name, label, 'read', 0]); if (got && got.found) seen.push([name, got.value || '']); }
    catch (e) {}
  }
  return seen;
}""".replace("@FIELD@", FIELD)


class Capture:
    """One held form's values as its pages last showed them on a press, by question name (`values`)."""

    def __init__(self):
        self.values: dict[str, str] = {}
        self._bound: set[int] = set()
        self._questions: list[list[str]] = []

    def watch(self, page, questions: list[Question]) -> None:
        """Put the listener into each frame of `page` that lacks it: on each turn of the held page, so a document the
        form loads (its next step) gets one too."""
        self._questions = [[q.name, q.label] for q in questions]
        if id(page) not in self._bound:
            try:
                page.expose_binding(BINDING, lambda source, said: self._take(said))
            except Exception:
                pass  # exposed already (a page held before, resumed): its binding still names this Capture's
            self._bound.add(id(page))
        for frame in _frames(page):
            try:
                frame.evaluate(LISTEN, self._questions)
            except Exception:
                continue  # a frame navigating, or one of another site that is gone

    def read_now(self, page) -> None:
        """Read the form as it is now (Approve and submit, just before Apply presses)."""
        for frame in _frames(page):
            try:
                self._keep(frame.evaluate(READ, self._questions))
            except Exception:
                continue

    def clear(self) -> None:
        """A new fill (Fill again): its values come anew."""
        self.values.clear()

    def _take(self, said: str) -> None:
        try:
            self._keep(json.loads(said))
        except (TypeError, ValueError):
            pass  # not the listener's own words

    def _keep(self, seen) -> None:
        for pair in seen if isinstance(seen, list) else []:
            if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str) and isinstance(pair[1], str):
                self.values[pair[0]] = pair[1][:20000]


def _frames(page) -> list:
    try:
        return list(page.frames)
    except Exception:
        return []
