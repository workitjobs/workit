"""Where Apply's secrets live (Employer account passwords, the WorkIt login, the Gmail app password, the ntfy
topic, API keys):
the system's keychain through `keyring`, which is macOS Keychain on a Mac and Credential Manager on
Windows. One item per service and account, which Lisul can see in Keychain Access. Never in the
Tracker, the repo or a log."""

import hmac
import threading

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

# The Keychain service every Employer account password is saved under; the
# item's account is the site (a Workday tenant's host, say).
EMPLOYER_ACCOUNTS = "apply-ats"
# The item, under EMPLOYER_ACCOUNTS, that holds the password Lisul chose in the Accounts tab for every new
# Employer account. No site has this name (a site is a host), so it never reads as an account.
CHOSEN = "all job sites"
# The WorkIt login's refresh token (apply.workit); the item's account is the Supabase URL it belongs to.
WORKIT = "apply-workit"
# The Gmail app password the mailbox signs in with; the item's account is the address.
GMAIL = "apply-gmail"
# The ntfy topic Lisul's phone subscribes to for pushes; the item's account is PHONE_PUSH_HOST.
# Anyone who knows a topic can read its pushes, so it is kept like a password.
PHONE_PUSH = "apply-ntfy"
PHONE_PUSH_HOST = "ntfy.sh"
# A developer's API keys for policies.yaml's ask_model (apply.ask_model); each item's account is the API's host.
GROQ = "apply-groq"
GROQ_HOST = "api.groq.com"
GEMINI = "apply-gemini"
GEMINI_HOST = "generativelanguage.googleapis.com"
# A developer's Claude setup token (`claude setup-token`), which `claude -p` signs in with before the claude login.
CLAUDE = "apply-claude"
CLAUDE_ACCOUNT = "setup-token"


class SystemKeychain:
    """The system's keychain through `keyring`. Each item's service is `service` and its account the site.
    `keyring` calls the system's own API in this process, so a password is in no command line that `ps`
    shows. Any failure (a locked keychain, access denied, no keychain at all) is a RuntimeError whose
    message never holds a password."""

    def __init__(self, service: str = EMPLOYER_ACCOUNTS, backend: KeyringBackend | None = None):
        """`backend` is a keyring backend to use instead of the system's (tests)."""
        self._service = service
        self._backend = backend

    def _store(self) -> KeyringBackend:
        return self._backend or keyring.get_keyring()

    def password(self, site: str) -> str | None:
        try:
            return self._store().get_password(self._service, site)
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not give the {self._service} item for {site}: {error}") from None

    def save(self, site: str, password: str) -> None:
        try:
            self._store().set_password(self._service, site, password)
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not save the {self._service} item for {site}: {error}") from None
        # A new account's password must be kept before its form is sent, and a backend that keeps nothing
        # (keyring's null one) raises no error: the save is read back.
        if not hmac.compare_digest((self.password(site) or "").encode(), password.encode()):
            raise RuntimeError(f"the keychain did not keep the {self._service} item for {site}")

    def forget(self, site: str) -> None:
        try:
            self._store().delete_password(self._service, site)
        except PasswordDeleteError as error:
            # keyring raises this when there is no such item too: that is nothing to remove.
            if self.password(site) is not None:
                raise RuntimeError(f"the keychain would not remove the {self._service} item for {site}: {error}") from None
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not remove the {self._service} item for {site}: {error}") from None


class InMemoryKeychain:
    """A Keychain for tests. Workers save from their own threads."""

    def __init__(self, passwords: dict[str, str] | None = None):
        self._passwords = dict(passwords or {})
        self._lock = threading.Lock()

    def password(self, site: str) -> str | None:
        with self._lock:
            return self._passwords.get(site)

    def save(self, site: str, password: str) -> None:
        with self._lock:
            self._passwords[site] = password

    def forget(self, site: str) -> None:
        with self._lock:
            self._passwords.pop(site, None)
