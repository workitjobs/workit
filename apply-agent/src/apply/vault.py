"""The sign-in vault: one saved login (email and password) per job portal host, which Apply types into that
host's sign-in page by itself when a tile pauses there (apply.vault_sign_in, docs/sign-in.md "Sign-in vault").

The logins sit behind `Store`, a small interface, so the place they are kept can change (the system's keychain
today; a password manager's CLI or Chrome's own autofill later) without a change to the code that fills them.
`KeyringStore` keeps each login as one item in the system's keychain through `keyring` (macOS Keychain on a Mac):
service `workit-apply:<host>`, account the email, password the password. A login is never written to disk, a
log, a Record, a screenshot or the window's state, and `Login`'s repr never shows its password.

A login is given only for an https page whose host is exactly the stored host (`host_of`): a lookalike domain,
a subdomain, an http page, another port or a URL with a user name in it gets nothing."""

import json
import re
import threading
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

PREFIX = "workit-apply:"
# keyring can't list a keychain's items, so the hosts and their emails (never a password) are one more item.
INDEX_SERVICE = "workit-apply"
INDEX_ACCOUNT = "hosts"

_LABEL = r"(?!-)[a-z0-9-]{1,63}(?<!-)"
_HOST = re.compile(rf"^{_LABEL}(?:\.{_LABEL})+$")


@dataclass(frozen=True)
class Login:
    host: str
    email: str
    password: str = field(repr=False)

    def __str__(self) -> str:
        return f"{self.email} at {self.host}"


class Store(Protocol):
    """Where the vault's logins are kept. Every method raises RuntimeError on a failure of the store, with a
    message that never holds a password."""

    def get(self, host: str) -> Login | None: ...

    def put(self, login: Login) -> None: ...

    def remove(self, host: str) -> bool: ...

    def hosts(self) -> list[tuple[str, str]]:
        """Each stored host and its email, sorted by host. Never a password."""
        ...


def host(text: str) -> str:
    """`text` as a vault host: a bare host name, lower case. A ValueError when it is a URL, has a port, a path or
    a user name, or is no host name at all: the vault matches hosts exactly, so it takes nothing looser."""
    name = text.strip().lower().rstrip(".")
    if not _HOST.match(name):
        raise ValueError(f"{text!r} is not a host name: give the sign-in page's host alone, like amazon.jobs "
                         "(no https://, no path, no port)")
    return name


def host_of(url: str) -> str | None:
    """The host a login may be given to on the page at `url`: its host on https with no user name and the default
    port, else None (an http page, a lookalike's URL that hides a host behind `user@`, a port)."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or parts.username is not None or parts.password is not None or port not in (None, 443):
        return None
    try:
        return host(parts.hostname or "")
    except ValueError:
        return None


def for_page(store: Store, url: str) -> Login | None:
    """The login for the page at `url`: only one stored for exactly its https host."""
    if not (name := host_of(url)):
        return None
    login = store.get(name)
    return login if login and login.host == name else None


class KeyringStore:
    """The system's keychain through `keyring`, in this process, so no password is in a command line that `ps`
    shows. `backend` is a keyring backend to use instead of the system's (tests)."""

    def __init__(self, backend: KeyringBackend | None = None):
        self._backend = backend
        self._lock = threading.Lock()

    def _ring(self) -> KeyringBackend:
        return self._backend or keyring.get_keyring()

    def _index(self) -> dict[str, str]:
        try:
            raw = self._ring().get_password(INDEX_SERVICE, INDEX_ACCOUNT)
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not give the vault's list of hosts: {error}") from None
        try:
            found = json.loads(raw) if raw else {}
        except ValueError:
            found = {}
        return {k: v for k, v in found.items() if isinstance(k, str) and isinstance(v, str)} \
            if isinstance(found, dict) else {}

    def _save_index(self, index: dict[str, str]) -> None:
        try:
            self._ring().set_password(INDEX_SERVICE, INDEX_ACCOUNT, json.dumps(index, sort_keys=True))
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not save the vault's list of hosts: {error}") from None

    def get(self, name: str) -> Login | None:
        name = host(name)
        email = self._index().get(name)
        if not email:
            return None
        try:
            password = self._ring().get_password(PREFIX + name, email)
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not give the vault's item for {name}: {error}") from None
        return Login(name, email, password) if password else None

    def put(self, login: Login) -> None:
        name = host(login.host)
        if not login.email or not login.password:
            raise RuntimeError("a vault login needs an email and a password")
        with self._lock:
            index = self._index()
            old = index.get(name)
            try:
                self._ring().set_password(PREFIX + name, login.email, login.password)
                stored = self._ring().get_password(PREFIX + name, login.email)
            except KeyringError as error:
                raise RuntimeError(f"the keychain would not save the vault's item for {name}: {error}") from None
            if stored != login.password:  # keyring's null backend drops a save and raises nothing
                raise RuntimeError(f"the keychain did not keep the vault's item for {name}")
            if old and old != login.email:
                self._delete(name, old)
            index[name] = login.email
            self._save_index(index)

    def remove(self, name: str) -> bool:
        name = host(name)
        with self._lock:
            index = self._index()
            email = index.pop(name, None)
            if email is None:
                return False
            self._delete(name, email)
            self._save_index(index)
            return True

    def hosts(self) -> list[tuple[str, str]]:
        return sorted(self._index().items())

    def _delete(self, name: str, email: str) -> None:
        try:
            self._ring().delete_password(PREFIX + name, email)
        except PasswordDeleteError:
            pass  # no such item: nothing to remove
        except KeyringError as error:
            raise RuntimeError(f"the keychain would not remove the vault's item for {name}: {error}") from None


class MemoryStore:
    """A Store for tests."""

    def __init__(self, *logins: Login):
        self._logins = {login.host: login for login in logins}

    def get(self, name: str) -> Login | None:
        return self._logins.get(host(name))

    def put(self, login: Login) -> None:
        self._logins[host(login.host)] = login

    def remove(self, name: str) -> bool:
        return self._logins.pop(host(name), None) is not None

    def hosts(self) -> list[tuple[str, str]]:
        return sorted((login.host, login.email) for login in self._logins.values())


# The store Apply's sign-in pauses read. A test or another backend sets it; None is the system's keychain.
STORE: Store | None = None


def store() -> Store:
    return STORE if STORE is not None else KeyringStore()
