"""Approve and submit (ADR 0006): the held form's own Submit, which Apply presses once the student approves it.

The page is the student's by then (the submit guard is off), so the press is the one they would make. Apply presses
only a button it is sure of: exactly one visible button, in the page or any of its frames, whose words send the
application (rehearsal.FINAL: Submit, Send). None, or more than one, and it presses nothing: the student presses it.
"""

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
    .filter(el => shown(el) && words(el).length <= 40 && /\b(submit|send)\b/i.test(words(el)));
  if (found.length === 1) found[0].setAttribute('data-apply-send', '');
  return found.map(words);
}"""

NONE = "Apply found no Submit button on the form, so it pressed nothing: press Submit on the page yourself."
SEVERAL = "The form shows more than one Submit button ({}), so Apply pressed none: press the right one yourself."


class NotPressed(Exception):
    """Apply couldn't tell which button sends the form: it pressed nothing, and the student presses it."""


def press(page) -> str:
    """Press the held form's one Submit button; its words. Raises NotPressed when there is none, or more than one."""
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
    frame.locator("[data-apply-send]").click(timeout=10_000)
    return words
