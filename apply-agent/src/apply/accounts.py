"""Lisul's Employer accounts and verification mail, as one Application uses
them while it signs in. Plain code, zero tokens.

- A new account's password is the one Lisul chose in the Accounts tab
  (keychain.CHOSEN), else a random one, and either keeps RULE. It is saved
  for the site before the sign-up form is sent, so a crash never leaves an
  account whose password is lost.
- A verification code or link is read from Gmail: looked for every few
  seconds for about 10 minutes. Apply never asks the site to send it again
  (no Resend or Send New Code click, anywhere): still nothing goes to Needs
  you ("Type the emailed code"), and Lisul retries himself. Gmail not set
  up goes there too.
- A failed password sign-in is a Handoff at once, and no Application tries
  that site's password again (Workday locks an account after a few
  failures), in this run or a later one.
"""

import re
import secrets
import string
from collections.abc import Callable
from datetime import datetime, timedelta

from apply.adapters import Clock, Keychain, Mailbox
from apply.keychain import CHOSEN
from apply.model import Handoff
from apply.tracker import EmployerAccount

# How long to look for a mail. It is asked for once per sign-in, never again, and
# some job systems take minutes to send it.
MAIL_WAIT = timedelta(minutes=10)
MAIL_POLL = timedelta(seconds=5)
# The rule every new account's password keeps, Lisul's own or a random one: a rule meant to suit almost every job
# site. Some sites take no more than 16 characters, and some refuse a symbol outside a short list, so the rule keeps
# to those. A site that refuses it still is a Handoff, which waits in Needs you.
LENGTHS = range(12, 17)
SYMBOLS = "!@#$%*"
RULE = "12 to 16 characters: an upper-case letter, a lower-case letter, a digit and one of ! @ # $ % *, and nothing else"
_KINDS = (string.ascii_uppercase, string.ascii_lowercase, string.digits, SYMBOLS)

# Starts the Handoff of an Application whose sign-in needs mail Gmail can't read.
NEEDS_SIGN_IN = "Needs sign-in: "
SIGN_IN_FAILED = "Sign-in failed at {site}: {why}"
SIGN_IN_FAILED_AT = re.compile(r"Sign-in failed at (\S+):")
NOT_RETRIED = (
    " Apply won't try that password again, here or for any other Posting there (a few failures lock the account): "
    "sign in yourself, and fix the password in Keychain (service apply-ats)."
)
SAVE_PASSWORD = ("Sign in there yourself and save the password in Keychain "
                 "(uv run keyring set apply-ats {site}, in apply-agent/).")
NO_PASSWORD = "{site} already has an account for {login}, and Keychain has no password for it. " + SAVE_PASSWORD
NO_RESET = (
    "{site} already has an account for {login}, and Keychain has no password for it. Apply resets its password "
    "through Gmail, but {why}. " + SAVE_PASSWORD
)
# A rehearsal (a reopened form's too) never resets a password (KAN-878's review): a reset changes the account
# Lisul uses, and a rehearsal only fills a form.
NO_RESET_IN_REHEARSAL = (NEEDS_SIGN_IN + "{site} already has an account for {login}, and Keychain has no password for it. "
                         "A rehearsal resets no password. " + SAVE_PASSWORD)
# A site refused a new account (KAN-838): its password is forgotten, and the form waits for Lisul in Needs you.
REFUSED = ("{site} refused the new account ({why}). If it refused the password, make the account on the page "
           "yourself with a password it takes, then finish the form.")
NO_MAIL = (
    NEEDS_SIGN_IN + "Type the emailed code: no {what} from {search} came within about {minutes} minutes, and Apply "
    "never asks for another. Check Gmail (spam too), then sign in and finish the application yourself."
)


class Accounts:
    def __init__(
        self,
        keychain: Keychain,
        mailbox: Mailbox,
        clock: Clock,
        login: str,
        company: str = "",
        on_created: Callable[[EmployerAccount], None] = lambda account: None,
        failed: set[str] | None = None,
        rehearsal: bool = False,
    ):
        """`login` is the email Lisul applies with. `on_created` lists a new
        account in the Tracker. `failed` holds the sites whose password
        sign-in has failed, shared by every Application of a run or
        Rehearsal. `rehearsal`: a Rehearsal's, which never resets a password
        that only may exist (workday.MAY_EXIST)."""
        self._keychain = keychain
        self._mailbox = mailbox
        self.clock = clock
        self.login = login
        self.company = company
        self._on_created = on_created
        self._failed = failed if failed is not None else set()
        self.rehearsal = rehearsal

    def password(self, site: str) -> str | None:
        """The site's password, if Apply made an account there. A Handoff if a
        sign-in with it has failed before."""
        if site in self._failed:
            raise Handoff(SIGN_IN_FAILED.format(site=site, why="an earlier sign-in with the Keychain password failed.") + NOT_RETRIED)
        return self._keychain.password(site)

    def new_password(self, site: str) -> str:
        """The password for an account about to be made at `site`, already
        saved for it: the one Lisul chose, else a new random one. The site
        keeps its own copy, so a password he chooses later is only for later
        accounts."""
        password = self._keychain.password(CHOSEN) or _generate()
        self._keychain.save(site, password)
        return password

    def reset_password(self, site: str) -> str:
        """A new password for the account at `site` that Lisul made himself
        and Keychain has none for, already in Keychain before the site is
        asked to reset it. Its reset link comes by mail, so this is a
        Handoff if Gmail can't be read, and in a rehearsal, which resets nothing: the new password it would have
        used is forgotten."""
        if self.rehearsal:
            self.not_made(site)
            raise Handoff(NO_RESET_IN_REHEARSAL.format(site=site, login=self.login))
        if why := self._mailbox.unavailable():
            raise Handoff(NO_RESET.format(site=site, login=self.login, why=why.rstrip(".")))
        return self.new_password(site)

    def not_made(self, site: str) -> None:
        """The site never made the account its new password was saved for:
        Keychain forgets it, so no later run signs in with it."""
        self._keychain.forget(site)

    def refused(self, site: str, why: str) -> Handoff:
        """The Handoff for a site that refused the new account: no account
        has its password, so Keychain forgets it."""
        self.not_made(site)
        return Handoff(REFUSED.format(site=site, why=why.strip().rstrip(".")))

    def created(self, site: str) -> None:
        """The site accepted the new account: list it in the Employer accounts tab."""
        self._on_created(EmployerAccount(self.company, site, self.login, self.clock.now().date()))

    def sign_in_failed(self, site: str, why: str) -> Handoff:
        """The Handoff for a refused password, which no Application tries again."""
        self._failed.add(site)
        why = why.strip()
        return Handoff(SIGN_IN_FAILED.format(site=site, why=why if why.endswith((".", "!", "?")) else why + ".") + NOT_RETRIED)

    def mail_unavailable(self) -> str | None:
        """Why Gmail can't be read (no app password), or None."""
        return self._mailbox.unavailable()

    def code(self, search: str, since: datetime) -> str:
        """The one-time code mailed since `since`, found by Gmail `search`."""
        return self._wait("verification code", search, since, self._mailbox.find_code)

    def link(self, search: str, since: datetime, hosts: tuple[str, ...]) -> str:
        """The verification link mailed since `since`, found by Gmail `search`,
        to one of `hosts` (the site's own, or its job system's). A rehearsal
        takes none from a mail that resets a password (KAN-878)."""
        return self._wait("verification email", search, since,
                          lambda **look: self._mailbox.find_link(**look, hosts=hosts, resets=not self.rehearsal))

    def mailed_link(self, search: str, since: datetime, hosts: tuple[str, ...]) -> str | None:
        """A verification link already mailed since `since`, in one look, or
        None: for an account made in an earlier run. Never waits, never asks."""
        if self._mailbox.unavailable():
            return None
        return self._mailbox.find_link(search=search, since=since, hosts=hosts, resets=not self.rehearsal)

    def _wait(self, what, search, since, find) -> str:
        """Gmail looked at until the mail comes or MAIL_WAIT passes. Never a
        second ask: a site may lock or rate-limit an account that asks again."""
        if why := self._mailbox.unavailable():
            raise Handoff(f"{NEEDS_SIGN_IN}{why.rstrip('.')}, so the {what} can't be read.")
        until = self.clock.now() + MAIL_WAIT
        while True:
            if found := find(search=search, since=since):
                return found
            if self.clock.now() >= until:
                raise Handoff(NO_MAIL.format(what=what, search=_senders(search), minutes=MAIL_WAIT // timedelta(minutes=1)))
            self.clock.sleep_until(self.clock.now() + MAIL_POLL)


def failed_sites(reasons: list[str]) -> set[str]:
    """The sites whose password sign-in failed, read off Tracker rows' reasons."""
    return {m[1] for reason in reasons for m in SIGN_IN_FAILED_AT.finditer(reason)}


def _senders(search: str) -> str:
    """A Gmail search's senders as words: "from:(a OR b)" is "a or b"."""
    return search.removeprefix("from:").removeprefix("(").removesuffix(")").replace(" OR ", " or ")


def broken_rule(password: str) -> str | None:
    """What a password Lisul chose lacks for RULE, or None when it keeps it."""
    if len(password) not in LENGTHS or not set(password) <= set("".join(_KINDS)) \
            or not all(set(password) & set(kind) for kind in _KINDS):
        return f"Use {RULE}."
    return None


def _generate() -> str:
    """A random password that keeps RULE, at its longest."""
    every = "".join(_KINDS)
    chars = [secrets.choice(kind) for kind in _KINDS] + [secrets.choice(every) for _ in range(LENGTHS[-1] - len(_KINDS))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
