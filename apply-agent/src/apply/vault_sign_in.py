"""Apply signs in from the vault (apply.vault) when a tile pauses at a sign-in. Plain code, zero tokens: no model
sees the page while the password is on it, and the password goes only from the store into the page's password
box. Docs: docs/sign-in.md, "Sign-in vault".

- Only on an https page whose host is exactly the stored host (vault.for_page), checked again just before the
  password is typed, so a page that moved to another host gets nothing.
- Only a plain sign-in: one password box that is no new password, an email or user name box, no name box, no
  captcha. A captcha, a code (2FA, OTP) and making an account stay the student's: the pause goes on as before.
  A captcha is never touched.
- Signed in means the password box stayed gone for SETTLED_S with no captcha. A password box that is still
  there, or back at the next sign-in pause of the same fill on that host, is a refused password: "Sign-in failed"
  once, and no tile types that password again in this run (a few failures lock an account). A password saved
  anew with `apply vault add` is tried again.
- Never on a page whose Chrome listens on a DevTools TCP port (a CDP Worker's, `debug_port`): any program on the
  Mac could attach there and read the password box. Only a plain Worker's page, which has no port, is signed in.
- The password boxes are emptied after the press, so no screenshot, Record or later model call reads one.
"""

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass

from apply import vault
from apply.vault import Login, Store

SIGNED_IN = "signed in"
FAILED = "failed"
LEFT = "left"  # the vault had no login for the page, or the page is not a plain sign-in: the student's
SETTLE_S = 15.0
SETTLED_S = 2.0  # the password box gone this long: a page that reloads with it after a refusal isn't signed in
POLL_MS = 250
EMPTY_MS = 2000

FAILED_WHY = ("Sign-in failed at {host}: the page still asks for the password after Apply typed the vault's login "
              "for {email}. Apply won't try it again in this run. Sign in yourself, and fix it with "
              "`uv run apply vault add {host}`.")
SIGNED_IN_NOTE = "Signed in from the vault as {email}"
NO_KEYCHAIN = "The vault couldn't read Keychain ({why}): sign in yourself."
OPEN_PORT = ("The vault has a login for {host}, but this Worker's Chrome listens on a DevTools port, where any "
             "program on this Mac could read a typed password: sign in yourself. A plain Worker has no port.")

_NOT = ":not([type=password]):not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=submit])"
_EMAIL = ", ".join(f"input{match}{_NOT}" for match in (
    "[type=email]", "[autocomplete=username]", "[autocomplete=email]", "[name*=email i]", "[id*=email i]",
    "[name*=user i]", "[id*=user i]", "[name*=login i]", "[id*=login i]"))
_PASSWORD = "input[type=password]"
# A box only a new account's form has: the vault never makes an account.
_SIGN_UP = ("input[autocomplete=new-password], input[autocomplete=given-name], input[autocomplete=family-name], "
            "input[name*=first i], input[name*=last i], input[id*=first i], input[id*=last i], "
            "input[name*=confirm i], input[id*=confirm i]")

# The logins whose password failed in this process (one run), by host, email and a keyed hash of the password,
# so a password saved anew is tried. The key is this process's alone: no hash of a password leaves it.
_failed: set[tuple[str, str, bytes]] = set()
_key = secrets.token_bytes(32)
_lock = threading.Lock()


@dataclass(frozen=True)
class Outcome:
    how: str
    why: str = ""
    said: bool = False  # `why` goes in the pause: the student must know the vault didn't sign in


def forget_run() -> None:
    """A new run (tests): every login may be tried again."""
    with _lock:
        _failed.clear()


def _mark(login: Login) -> tuple[str, str, bytes]:
    return login.host, login.email.lower(), hmac.new(_key, login.password.encode(), hashlib.sha256).digest()


def sign_in(page, tried: set[str], store: Store | None = None, let_press=None, settle_s: float | None = None) -> Outcome:
    """Type the vault's login for `page`'s host into its sign-in and press it. The host is read from the page's
    own URL now, never from the tile. `tried` holds the hosts this fill has signed in to already (the caller's,
    one per fill): each is typed once, and a password box there again is a refused password. `let_press(page,
    let)` lets the press through the submit guards (submit_guard.let_account_click), as a sign-in step's press."""
    try:
        login = vault.for_page(store if store is not None else vault.store(), page.url)
    except RuntimeError as error:  # the keychain locked or refused: the pause is the student's, and says why
        return Outcome(LEFT, NO_KEYCHAIN.format(why=error), said=True)
    if login is None:
        return Outcome(LEFT)
    if debug_port(page):  # before any box is touched: a program on the port could read the password from it
        return Outcome(LEFT, OPEN_PORT.format(host=login.host), said=True)
    with _lock:
        failed = _mark(login) in _failed
    if failed:
        return Outcome(FAILED, FAILED_WHY.format(host=login.host, email=login.email))
    if login.host in tried:
        if _visible(page, _PASSWORD):  # signed in "by" the vault, and asked for the password again: refused
            return _refused(login)
        return Outcome(LEFT)
    tried.add(login.host)
    if let_press is None:
        from apply.submit_guard import let_account_click as let_press
    typed = [False]
    try:
        return _sign_in(page, login, let_press, SETTLE_S if settle_s is None else settle_s, typed)
    finally:
        if typed[0]:
            _empty(page)


def debug_port(page) -> bool:
    """Whether `page`'s Chrome listens on a DevTools TCP port. A CDP Worker's does (`--remote-debugging-port=0`,
    browsers.launch_options: Claude fill's Playwright MCP, the tile's screencast and Show attach there), and any
    local program may attach to it. A plain Worker's Chrome has none (plain.launcher.NEVER). A page that is no
    Playwright page (a test's stand-in) has no browser at all."""
    from apply.plain.page import PortPage

    if isinstance(page, PortPage):
        return False
    return hasattr(page, "context")  # a Playwright page: a CDP Worker's, or one this code can't tell from it


def _refused(login: Login) -> Outcome:
    with _lock:
        _failed.add(_mark(login))
    return Outcome(FAILED, FAILED_WHY.format(host=login.host, email=login.email))


def _sign_in(page, login: Login, let_press, settle_s: float, typed: list[bool]) -> Outcome:
    if _captcha(page):
        return Outcome(LEFT, "a captcha shows")
    passwords = _visible(page, _PASSWORD)
    if not passwords:  # an email-first step (Amazon's, iCIMS's): its email, then the password step
        emails = _visible(page, _EMAIL)
        if len(emails) != 1 or _visible(page, _SIGN_UP):
            return Outcome(LEFT, "no sign-in boxes")
        emails[0].fill(login.email)
        _press(page, emails[0], let_press)
        passwords = _until(page, lambda: _visible(page, _PASSWORD), settle_s)
        if not passwords or _captcha(page):
            return Outcome(LEFT, "no password step after the email")
    if len(passwords) != 1:
        return Outcome(LEFT, "more than one password box (a sign-up or a password change)")
    if _visible(page, _SIGN_UP):
        return Outcome(LEFT, "a new account's form")
    emails = _visible(page, _EMAIL)
    if len(emails) > 1:
        return Outcome(LEFT, "more than one email box")
    if vault.host_of(page.url) != login.host:  # the page moved (the email step's press): never another host's
        return Outcome(LEFT, "the page left the stored host")
    if emails and (emails[0].input_value() or "").strip().lower() != login.email.lower():
        emails[0].fill(login.email)
    typed[0] = True
    passwords[0].fill(login.password)
    _press(page, passwords[0], let_press)
    if _until(page, lambda: _gone_for(page, SETTLED_S), settle_s + SETTLED_S):
        if _captcha(page):  # a captcha after the press: the student's, and no sign-in yet
            return Outcome(LEFT, "a captcha shows")
        return Outcome(SIGNED_IN, SIGNED_IN_NOTE.format(email=login.email))
    return _refused(login)


def _gone_for(page, seconds: float) -> bool:
    """No password box shows now, nor at any look for `seconds`: a page that reloads with it after a refusal
    shows it again within that."""
    end = time.monotonic() + seconds
    while True:
        if _visible(page, _PASSWORD):
            return False
        if time.monotonic() >= end:
            return True
        page.wait_for_timeout(POLL_MS)


def _press(page, box, let_press) -> None:
    """Enter in the box: the form's own sign-in, through the guards as a sign-in step's press (KAN-868)."""
    let_press(page, True)
    try:
        box.press("Enter")
    finally:
        let_press(page, False)


def _until(page, check, seconds: float):
    end = time.monotonic() + seconds
    while True:
        try:
            if found := check():
                return found
        except Exception:
            pass  # the page navigating: look again
        if time.monotonic() >= end:
            return None
        page.wait_for_timeout(POLL_MS)


def _visible(page, selector: str) -> list:
    found = []
    try:
        boxes = page.locator(selector).all()
    except Exception:
        return found  # the page navigating
    for box in boxes:
        try:
            if box.is_visible():
                found.append(box)
        except Exception:
            continue
    return found


def _captcha(page) -> bool:
    from apply import captcha

    try:
        return bool(captcha.pending(page))
    except Exception:
        return True  # can't tell: leave it to the student


def _empty(page) -> None:
    """Every password box emptied, a hidden one too: no screenshot, Record or later read of the page holds the
    password. A short wait each: a box gone meanwhile never holds the pause up."""
    try:
        page.evaluate("() => document.querySelectorAll('input[type=password]').forEach(box => { box.value = ''; })")
    except Exception:
        pass  # the page navigating, or a stand-in page: the boxes that show are emptied below
    for box in _visible(page, _PASSWORD):
        try:
            box.fill("", timeout=EMPTY_MS)
        except Exception:
            pass
