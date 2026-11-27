"""A code step after the student's approved Submit with a button of its own: Oracle's "You're almost done" (six
one-digit boxes, VERIFY, Send New Code). The code given in the window (`apply window code`) goes in, Apply presses
VERIFY, never Send New Code, and the thank-you page marks it sent. An expired code gets Send New Code pressed and the
newest code asked for. A fake Oracle page, in a real browser."""

import threading

from test_rehearse import OnePage

from apply import code_box, rehearsal

URL = "https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26013632/apply/section/1"
CODE, OLD = "182876", "554433"

# The form's Submit leads to Oracle's post-submit code step. The right code and VERIFY show Oracle's thanks; the old
# one shows the expiry Oracle words; Send New Code takes that away (a new code is mailed).
PAGE = """<!doctype html><title>Oracle</title>
<div id="form"><label>Phone<input value="5555550100"></label><button id="submit" type="button">Submit</button></div>
<script>
  window.clicks = [];
  document.addEventListener('click', e => { const b = e.target.closest('button'); if (b) window.clicks.push(b.textContent); }, true);
  const boxes = [1, 2, 3, 4, 5, 6].map(n => `<input class="pin-code-input" inputmode="numeric" maxlength="1"
    aria-label="Enter verification code digit ${n} of six.">`).join('');
  document.getElementById('submit').onclick = () => {
    document.getElementById('form').outerHTML = `<div id="step"><h1>You're almost done</h1>
      <p>The verification code was sent to this email address: t***@example.com. When you get the code, type the code
      into the field to confirm your identity and complete your job application.</p><div>${boxes}</div>
      <button id="verify" type="button">VERIFY</button><button id="resend" type="button">Send New Code</button></div>`;
    const code = () => [...document.querySelectorAll('.pin-code-input')].map(i => i.value).join('');
    document.getElementById('verify').onclick = () => {
      if (code() === '""" + CODE + """') document.getElementById('step').outerHTML = '<h1>Thank you for your job application.</h1>';
      else if (!document.querySelector('[role=alert]')) document.getElementById('step').insertAdjacentHTML('beforeend',
        '<div role="alert">The verification code has expired. Request a new code.</div>');
    };
    document.getElementById('resend').onclick = () => document.querySelector('[role=alert]')?.remove();
  };
</script>"""


def hold(*given: str):
    """Hold the page with Submit approved once, then each code of `given` typed in the window once the last was
    answered. Returns what the window was told (code_said), whether it was marked sent, and the page's clicks."""
    release, said, sent, codes, approvals = threading.Event(), [], [], list(given), [True]
    watchdog = threading.Timer(30, release.set)
    watchdog.start()

    def code_given() -> str:
        return codes.pop(0) if codes and not approvals and len(said) == len(given) - len(codes) else ""

    def submitted(page) -> None:
        sent.append(True)
        release.set()
    site = rehearsal._Kept(OnePage(PAGE), 0)
    try:
        with site.open(URL) as opened:
            site.hold(release, job_system="oracle", submitted=submitted, approve=lambda: bool(approvals and approvals.pop()),
                      code_given=code_given, code_said=said.append)
            clicks = opened.evaluate("window.clicks")
    finally:
        watchdog.cancel()
    return said, sent, clicks


def test_the_code_goes_in_and_verify_finishes_the_approved_submit():
    """Fault (Emerson, live 2026-11-27): `apply window code` typed the six digits, but the press after them landed on
    Send New Code, never VERIFY, and the window said the site never showed that it went in."""
    said, sent, clicks = hold(CODE)

    assert clicks == ["Submit", "VERIFY"]
    assert sent and said == [""]


def test_an_expired_code_gets_a_new_one_sent_and_the_newest_code_goes_in():
    """Fault: a code that expired left the step stuck: no new code was asked for, nor the student told to give one."""
    said, sent, clicks = hold(OLD, CODE)

    assert clicks == ["Submit", "VERIFY", "Send New Code", "VERIFY"]
    assert said == [code_box.EXPIRED_SENT, ""] and sent
