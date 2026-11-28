"""A sign-in's emailed code given in the window (`apply window code`) on a form held at its sign-in: Oracle's
"Confirm your identity" one-time code, which the Student build can't read from mail. Apply enters it, presses the
step's own Verify (never a Submit), and the paused fill goes on. A fake Oracle code page, in a real browser."""

import threading

import pytest
from test_rehearse import OnePage

from apply import code_box, rehearsal

URL = "https://hdow.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1003/job/250630"
CODE = "482913"

# Oracle's code step, as tests/fake_oracle.py draws it: six one-digit boxes, Verify and Send New Code. Its Submit
# stands for any button that would send an application: Apply never presses it. A right code turns the page into
# the application form (no code boxes); a wrong one shows Oracle's alert.
PAGE = """<!doctype html><title>Oracle</title>
<div id="step">
  <h2>Confirm Your Identity</h2><p>Enter the verification code we sent to t***@example.com.</p>
  <div>{boxes}</div>
  <button id="verify" type="button">Verify</button>
  <button id="resend" type="button">Send New Code</button>
  <button id="submit" type="button">Submit</button>
</div>
<script>
  window.clicks = [];
  document.addEventListener('click', e => {{ const b = e.target.closest('button'); if (b) window.clicks.push(b.textContent); }}, true);
  const code = () => [...document.querySelectorAll('.pin-code-input')].map(i => i.value).join('');
  document.getElementById('verify').onclick = () => {{
    if (code() === '{code}') document.getElementById('step').outerHTML = '<h1>Application form</h1><label>Phone<input></label>';
    else if (!document.querySelector('[role=alert]')) document.getElementById('step').insertAdjacentHTML('beforeend', '<div role="alert">Invalid code. Try again.</div>');
  }};
</script>"""
BOXES = "".join(f'<input class="pin-code-input" maxlength="1" aria-label="Verification code digit {n}">' for n in range(1, 7))


def hold(given: str, signing_in: bool = True):
    """Hold the Oracle code page as a paused rehearsal does, with `given` typed in the window once. Returns how the
    hold ended, what the window was told (code_said), and the page's clicks."""
    release, said, codes = threading.Event(), [], [given]
    watchdog = threading.Timer(30, release.set)
    watchdog.start()

    def code_said(why: str) -> None:
        said.append(why)
        if why:
            release.set()

    def resume(page) -> bool:  # oracle.signed_in's own check: the application form, past the code
        return page.get_by_text("Application form").count() > 0
    site = rehearsal._Kept(OnePage(PAGE.format(boxes=BOXES, code=CODE)), 0)
    try:
        with site.open(URL) as opened:
            how = site.hold(release, resume=resume, signing_in=signing_in,
                            code_given=lambda: codes.pop() if codes else "", code_said=code_said)
            clicks = opened.evaluate("window.clicks")
    finally:
        watchdog.cancel()
    return how, said, clicks


def test_a_sign_in_code_given_in_the_window_signs_in_and_the_fill_goes_on_with_no_submit_pressed():
    """Fault (BGC/Cantor on Oracle, 2026-11-27): `apply window code` on a form held at its sign-in said "Submit
    wasn't pressed on this form yet", so no one could give Oracle's code, and the form stalled at sign-in."""
    how, said, clicks = hold(CODE)

    assert how == rehearsal.RESUME  # the paused fill goes on
    assert said == [""]  # the window says it went in
    assert clicks == ["Verify"]  # the step's own button: never Submit, never Send New Code


def test_a_wrong_sign_in_code_is_said_and_nothing_else_is_pressed():
    """Fault: a code Oracle refuses reads as signed in, or Apply presses Verify again (Oracle locks after 4 tries)."""
    how, said, clicks = hold("111111")

    assert said == [code_box.WRONG_CODE] and clicks == ["Verify"]
    assert how == ""  # still held for the student: the window's release ended it here


def test_a_code_on_a_form_not_held_at_a_sign_in_still_waits_for_submit():
    """Fault: a code given before any Submit on an application form (no sign-in) is entered, and Submit pressed."""
    _, said, clicks = hold(CODE, signing_in=False)

    assert said == [code_box.NOT_SENT_YET] and clicks == []


@pytest.mark.parametrize("words, goes_on", [("Verify", True), ("Continue", True), (" Next ", True), ("Submit", False),
                                            ("Submit application", False), ("Send New Code", False), ("Send", False)])
def test_only_a_sign_in_steps_own_button_is_pressed(words, goes_on):
    """Fault: the sign-in's press lands on a Submit or Send, which may send an application, or on Send New Code."""
    assert bool(code_box.GO_ON.match(words)) is goes_on
