"""The Accounts tab of the Apply window (KAN-591): each Employer account Apply made, so Lisul can sign in to it
himself later, to check an application's status, and the one password he chooses for every new account (KAN-838).

A password lives in Keychain. Show password sends one account's password to the window when he presses it. Copy
password does the same, and the window writes it to the clipboard itself (`navigator.clipboard.writeText`), as its
other copy buttons do: no clipboard code in Apply, so it works on every OS (W4, D35). The passwords are his, and
keeping one from him is not a requirement: there are no secret marks and no clear after a minute. Neither button
puts a password in a log, a Trace or a Record, and the tab keeps no copy."""

from collections.abc import Callable
from urllib.parse import urlsplit

from apply import captcha, fill_engine
from apply.accounts import RULE, broken_rule
from apply.adapters import Keychain
from apply.answers_tab import Refused
from apply.chrome_finder import NO_CHROME
from apply.keychain import CHOSEN
from apply.tracker import EmployerAccount


class AccountsTab:
    """`accounts` reads the Tracker's Employer accounts list; `keychain` holds their passwords; `rows` reads the
    Tracker's rows, for each account's Posting link. `everyday` opens a link in Lisul's everyday Chrome."""

    def __init__(self, accounts: Callable[[], list[EmployerAccount]], keychain: Keychain,
                 rows: Callable[[], list] = list, everyday: Callable[[str], None] = captcha.to_everyday_chrome):
        self._accounts = accounts
        self._keychain = keychain
        self._rows = rows
        self._everyday = everyday

    def view(self) -> dict:
        """Each account, newest first, with no password; whether Lisul chose a password, and its rule."""
        listed = sorted(self._accounts(), key=lambda a: a.created, reverse=True)
        try:
            chosen = self._keychain.password(CHOSEN) is not None
        except RuntimeError:  # Keychain is locked: the tab offers to choose one, and saving says why it can't
            chosen = False
        return {"accounts": [{"company": a.company, "site": a.site, "login": a.login, "created": a.created.isoformat()}
                             for a in listed], "chosen": chosen, "rule": RULE}

    def choose(self, password: object) -> str:
        """Save the password Lisul chose for every new account. Accounts made before keep their own."""
        if not isinstance(password, str) or (why := broken_rule(password)):
            raise Refused(why if isinstance(password, str) else "Not a password.", 400)
        try:
            self._keychain.save(CHOSEN, password)
        except RuntimeError:
            raise Refused("Keychain did not save the password. Unlock Keychain and try again.", 502) from None
        return "Saved. Apply uses this password for each new account. Accounts made before keep their own."

    def show(self, site: object) -> str:
        """The password of the listed account at `site`, for the window to show when Lisul presses Show password,
        or to write to the clipboard when he presses Copy password. Only a site in the Employer accounts list is
        read: the page cannot name any other Keychain item."""
        return self._password(self._listed(site))

    def open_sign_in(self, site: object) -> str:
        """Open the listed account's sign-in in Lisul's everyday Chrome (never over DevTools): the newest Posting
        of its site in the Tracker, whose page has Sign In in its header, else the site's home."""
        account = self._listed(site)
        host = account.site.partition("/")[0]
        postings = [str(row.posting_url) for row in self._rows() if urlsplit(str(row.posting_url)).hostname == host]
        if "/" in account.site:  # a myworkdaysite.com tenant: host/<site>, as the engine names it
            postings = [url for url in postings if (fill_engine.job_of(url) or {}).get("tenant") == account.site]
        try:
            self._everyday(postings[-1] if postings else f"https://{host}/")
        except FileNotFoundError:
            raise Refused(NO_CHROME, 404) from None
        return f"Opened {account.company or account.site} in your Chrome: press Sign In there, and paste the password."

    def _password(self, account: EmployerAccount) -> str:
        try:
            password = self._keychain.password(account.site)
        except RuntimeError:  # Keychain is locked, or Lisul denied it
            raise Refused("Keychain did not give Apply the password. Unlock Keychain and try again.", 502) from None
        if not password:
            raise Refused(f"Keychain has no password for {account.site}. Apply made no password for it, "
                          "or it was made with Google.", 404)
        return password

    def _listed(self, site: object) -> EmployerAccount:
        account = next((a for a in self._accounts() if a.site == site), None)
        if account is None:
            raise Refused("Apply made no account there.", 404)
        return account
