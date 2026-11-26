"""Contract tests every Keychain must pass: the in-memory one tests use, and the system's keychain through
`keyring`, over a fake backend here. With APPLY_TEST_KEYCHAIN=1 they also run on the real one (macOS
Keychain, Windows Credential Manager) under the service apply-ats-test, whose items each test removes:
never an apply-ats item. keyring's macOS backend ignores a keychain file, so this is the login keychain."""

import os

import keyring
import pytest
from keyring.backend import get_all_keyring
from keyring.backends import chainer, fail, null
from keyring.errors import KeyringLocked, PasswordDeleteError

from apply.keychain import InMemoryKeychain, SystemKeychain

SITES = ["acme.wd5.myworkdayjobs.com", "other.wd1.myworkdayjobs.com", "never.wd1.myworkdayjobs.com"]


class FakeBackend:
    """A keyring backend in a dict that acts as macOS's and Windows' do: removing no item raises."""

    def __init__(self):
        self.items = {}

    def get_password(self, service, username):
        return self.items.get((service, username))

    def set_password(self, service, username, password):
        self.items[(service, username)] = password

    def delete_password(self, service, username):
        if self.items.pop((service, username), None) is None:
            raise PasswordDeleteError(service)


def _system_backend():
    """The system's own keyring backend: the best one keyring finds, never a chain, the null or the fail one."""
    found = [k for k in get_all_keyring() if not isinstance(k, chainer.ChainerBackend | null.Keyring | fail.Keyring)]
    return max(found, key=lambda k: k.priority) if found else pytest.skip("no system keychain here")


@pytest.fixture(params=["memory", "keyring", "system"])
def keychain(request):
    if request.param == "memory":
        yield InMemoryKeychain()
        return
    if request.param == "keyring":
        yield SystemKeychain("apply-ats-test", backend=FakeBackend())
        return
    if not os.environ.get("APPLY_TEST_KEYCHAIN"):
        pytest.skip("set APPLY_TEST_KEYCHAIN=1 to use the system's keychain, under the service apply-ats-test")
    real = SystemKeychain("apply-ats-test", backend=_system_backend())
    try:
        yield real
    finally:
        for site in SITES:
            real.forget(site)


def test_a_site_with_no_password_has_none(keychain):
    assert keychain.password("acme.wd5.myworkdayjobs.com") is None


def test_a_saved_password_is_read_back_by_site(keychain):
    keychain.save("acme.wd5.myworkdayjobs.com", "Pa55-word!")
    keychain.save("other.wd1.myworkdayjobs.com", "Different#9")

    assert keychain.password("acme.wd5.myworkdayjobs.com") == "Pa55-word!"
    assert keychain.password("other.wd1.myworkdayjobs.com") == "Different#9"


def test_saving_again_replaces_the_password(keychain):
    keychain.save("acme.wd5.myworkdayjobs.com", "first-One1!")
    keychain.save("acme.wd5.myworkdayjobs.com", "second-Two2!")

    assert keychain.password("acme.wd5.myworkdayjobs.com") == "second-Two2!"


def test_a_forgotten_password_is_gone_and_others_stay(keychain):
    keychain.save("acme.wd5.myworkdayjobs.com", "Pa55-word!")
    keychain.save("other.wd1.myworkdayjobs.com", "Different#9")

    keychain.forget("acme.wd5.myworkdayjobs.com")
    keychain.forget("never.wd1.myworkdayjobs.com")  # no password there: nothing to remove

    assert keychain.password("acme.wd5.myworkdayjobs.com") is None
    assert keychain.password("other.wd1.myworkdayjobs.com") == "Different#9"


def test_passwords_with_shell_characters_survive(keychain):
    password = "a'b\"c $d `e` \\f;g|h&i"
    keychain.save("acme.wd5.myworkdayjobs.com", password)

    assert keychain.password("acme.wd5.myworkdayjobs.com") == password


def test_a_save_that_a_backend_does_not_keep_fails():
    # A new account's password must be kept before its form is sent; keyring's null backend drops it silently.
    with pytest.raises(RuntimeError, match="did not keep"):
        SystemKeychain(backend=null.Keyring()).save("acme.wd5.myworkdayjobs.com", "Fake-Pw-1!q")


class LockedBackend(FakeBackend):
    def get_password(self, *args):
        raise KeyringLocked("Can't get password from keychain: (-25308, 'User interaction is not allowed.')")

    set_password = delete_password = get_password


@pytest.mark.parametrize("use", [lambda k: k.password("acme.wd5.myworkdayjobs.com"),
                                 lambda k: k.save("acme.wd5.myworkdayjobs.com", "Fake-Pw-1!q"),
                                 lambda k: k.forget("acme.wd5.myworkdayjobs.com")])
def test_a_locked_keychain_is_a_runtime_error_with_no_password_in_it(use):
    # Callers (the Accounts tab's Copy password, say) catch RuntimeError, never keyring's own errors.
    with pytest.raises(RuntimeError) as refused:
        use(SystemKeychain(backend=LockedBackend()))

    assert "acme.wd5.myworkdayjobs.com" in str(refused.value) and "Fake-Pw-1!q" not in str(refused.value)


def test_tests_never_reach_the_system_keychain():
    # conftest.py puts keyring's null backend in place: a SystemKeychain no test gave a backend reads nothing.
    assert isinstance(keyring.get_keyring(), null.Keyring)
    assert SystemKeychain().password("acme.wd5.myworkdayjobs.com") is None
