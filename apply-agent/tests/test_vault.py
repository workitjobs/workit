"""The sign-in vault's store and host matching (apply.vault). No test reaches the system's keychain: the keyring
store runs over a fake backend."""

import pytest
from keyring.backends import null
from keyring.errors import PasswordDeleteError

from apply import vault
from apply.vault import KeyringStore, Login, MemoryStore

SECRET = "Hunter2!Secret"


class FakeBackend:
    """A keyring backend in a dict that acts as macOS's does: removing no item raises."""

    def __init__(self):
        self.items = {}

    def get_password(self, service, username):
        return self.items.get((service, username))

    def set_password(self, service, username, password):
        self.items[(service, username)] = password

    def delete_password(self, service, username):
        if self.items.pop((service, username), None) is None:
            raise PasswordDeleteError(service)


@pytest.fixture(params=["memory", "keyring"])
def store(request):
    return MemoryStore() if request.param == "memory" else KeyringStore(backend=FakeBackend())


def test_a_saved_login_comes_back_and_goes(store):
    store.put(Login("amazon.jobs", "me@example.com", SECRET))
    assert store.get("amazon.jobs") == Login("amazon.jobs", "me@example.com", SECRET)
    assert store.hosts() == [("amazon.jobs", "me@example.com")]
    assert store.remove("amazon.jobs") is True
    assert store.get("amazon.jobs") is None
    assert store.remove("amazon.jobs") is False
    assert store.hosts() == []


def test_a_new_email_replaces_the_old_item():
    backend = FakeBackend()
    store = KeyringStore(backend=backend)
    store.put(Login("amazon.jobs", "old@example.com", SECRET))
    store.put(Login("amazon.jobs", "new@example.com", "Other1!Secret"))
    assert ("workit-apply:amazon.jobs", "old@example.com") not in backend.items
    assert backend.items[("workit-apply:amazon.jobs", "new@example.com")] == "Other1!Secret"
    assert store.hosts() == [("amazon.jobs", "new@example.com")]


def test_each_login_is_one_item_per_host_and_the_list_holds_no_password():
    backend = FakeBackend()
    KeyringStore(backend=backend).put(Login("acme.wd5.myworkdayjobs.com", "me@example.com", SECRET))
    assert backend.items[("workit-apply:acme.wd5.myworkdayjobs.com", "me@example.com")] == SECRET
    assert SECRET not in backend.items[(vault.INDEX_SERVICE, vault.INDEX_ACCOUNT)]


def test_a_save_the_keychain_drops_raises():
    with pytest.raises(RuntimeError, match="did not keep"):
        KeyringStore(backend=null.Keyring()).put(Login("amazon.jobs", "me@example.com", SECRET))


def test_a_login_never_shows_its_password():
    login = Login("amazon.jobs", "me@example.com", SECRET)
    assert SECRET not in repr(login) and SECRET not in str(login) and SECRET not in f"{login}"


@pytest.mark.parametrize("text", ["https://amazon.jobs", "amazon.jobs/login", "amazon.jobs:443", "me@amazon.jobs",
                                  "localhost", "amazon .jobs", "", "-bad.com"])
def test_only_a_bare_host_is_a_vault_host(text):
    with pytest.raises(ValueError):
        vault.host(text)


def test_a_host_is_kept_in_lower_case():
    assert vault.host(" Amazon.Jobs. ") == "amazon.jobs"


@pytest.mark.parametrize("url", [
    "https://amazon.jobs/en/login",
    "https://AMAZON.JOBS/en/login?next=/x",
    "https://amazon.jobs:443/en/login",
])
def test_the_exact_https_host_gets_its_login(url):
    store = MemoryStore(Login("amazon.jobs", "me@example.com", SECRET))
    assert vault.for_page(store, url).password == SECRET


@pytest.mark.parametrize("url", [
    "http://amazon.jobs/en/login",  # not https
    "https://amazon.jobs.evil.com/login",  # a lookalike that starts with the host
    "https://evil-amazon.jobs/login",
    "https://amazonjobs.com/login",
    "https://www.amazon.jobs/login",  # a subdomain is another host
    "https://amazon.jobs@evil.com/login",  # the host is evil.com
    "https://evil.com/?https://amazon.jobs/",
    "https://amazon.jobs:8443/login",
    "https://xn--amazn-mye.jobs/login",  # punycode lookalike
    "javascript:alert(1)",
    "about:blank",
    "",
])
def test_any_other_page_gets_nothing(url):
    store = MemoryStore(Login("amazon.jobs", "me@example.com", SECRET))
    assert vault.for_page(store, url) is None


def _cli(*args, inputs=("me@example.com",), secrets=(SECRET, SECRET), terminal=True, store=None):
    from apply import cli

    store = store if store is not None else MemoryStore()
    given, hidden = iter(inputs), iter(secrets)
    cli._vault(*args, store=store, ask=lambda prompt: next(given), secret=lambda prompt: next(hidden),
               terminal=lambda: terminal)
    return store


def test_vault_add_asks_for_the_password_and_never_prints_it(capsys):
    store = _cli("add", "amazon.jobs", None)
    assert store.get("amazon.jobs") == Login("amazon.jobs", "me@example.com", SECRET)
    out = capsys.readouterr()
    assert SECRET not in out.out + out.err


def test_vault_add_refuses_piped_input_and_a_url():
    with pytest.raises(SystemExit, match="terminal"):
        _cli("add", "amazon.jobs", "me@example.com", terminal=False)
    with pytest.raises(SystemExit, match="not a host name"):
        _cli("add", "https://amazon.jobs/login", "me@example.com")
    with pytest.raises(SystemExit, match="not the same"):
        _cli("add", "amazon.jobs", "me@example.com", secrets=(SECRET, "other"))


def test_vault_takes_no_password_argument():
    from apply import cli

    with pytest.raises(SystemExit):
        cli.main(["vault", "add", "amazon.jobs", "--password", SECRET])


def test_vault_list_and_remove(capsys):
    store = MemoryStore(Login("amazon.jobs", "me@example.com", SECRET))
    _cli("list", "", None, store=store)
    assert capsys.readouterr().out.strip() == "amazon.jobs\tme@example.com"
    _cli("remove", "amazon.jobs", None, store=store)
    assert store.hosts() == []
    out = capsys.readouterr().out
    assert SECRET not in out
