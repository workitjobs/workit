"""`apply login` and the WorkIt client, against a fake WorkIt (fake_workit.py).

The student signs in to WorkIt in their own browser one time, and Apply trades
the page's code for a session of its own (W5); Apply keeps its refresh token in
the keychain and refreshes its access token by itself."""

import re

import pytest
from fake_workit import FakeWorkIt

from apply import workit
from apply.home import CODE
from apply.workit import LoginExpired, NotLoggedIn, SignInOver, Unreachable, WorkIt


def logged_in(fake, tmp_path) -> WorkIt:
    client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
    workit.login(client, fake.browser)
    fake.requests.clear()
    return client


def test_login_keeps_only_the_refresh_token_in_the_keychain(tmp_path):
    with FakeWorkIt() as fake:
        old = tmp_path / "workit-login.json"
        old.write_text('{"refresh_token": "old"}')  # the session file Apply kept before 2026-11-15
        client = WorkIt(fake.site, old, fake.keychain)
        pages = []
        account = workit.login(client, lambda url: pages.append(url) or fake.browser(url))

        assert pages[0].startswith(f"{fake.url}/app-sign-in?challenge=")
        assert account.email == "test.person@example.com"
        assert fake.keychain.password(fake.site.auth) == "refresh-1"
        assert not old.exists()
        # Another client in this process shares its access token; another process refreshes once, and keeps
        # the rotated refresh token.
        fake.requests.clear()
        assert WorkIt(fake.site, old, fake.keychain).me().email == "test.person@example.com"
        assert [r.path for r in fake.requests] == ["/auth/me"]
        workit._ACCESS.clear()
        assert WorkIt(fake.site, old, fake.keychain).me().email == "test.person@example.com"
        assert fake.keychain.password(fake.site.auth) == "refresh-2"


def test_a_code_another_sign_in_got_is_refused_and_keeps_no_login(tmp_path):
    with FakeWorkIt() as fake:
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        other = fake.browser(workit.sign_in_page(fake.site, workit.pkce()[1]))

        with pytest.raises(SignInOver):
            workit.login(client, lambda url: other)
        assert not client.logged_in()


def test_the_pages_link_pasted_in_place_of_its_code_signs_in(tmp_path):
    """Fault: the pasted `workit-auto-apply://` link sent as the code, which WorkIt refuses."""
    with FakeWorkIt() as fake:
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        account = workit.login(client, lambda url: f"workit-auto-apply://signed-in?code={fake.browser(url)}\n")
        assert account.email == "test.person@example.com"


def test_an_expired_access_token_is_refreshed_without_a_new_sign_in(tmp_path):
    with FakeWorkIt() as fake:
        client = logged_in(fake, tmp_path)
        fake.expire()

        assert client.me().email == "test.person@example.com"
        # Supabase rotates the refresh token: the new one is kept, so the next refresh works too.
        assert fake.keychain.password(fake.site.auth) == "refresh-2"
        fake.expire()
        assert client.me().email == "test.person@example.com"
        assert fake.keychain.password(fake.site.auth) == "refresh-3"


def test_an_access_token_near_its_end_is_refreshed_before_it_is_sent(tmp_path):
    with FakeWorkIt() as fake:
        fake.lifetime = 30
        client = logged_in(fake, tmp_path)

        assert client.me().email == "test.person@example.com"
        assert [r.path for r in fake.requests] == ["/auth/v1/token?grant_type=refresh_token", "/auth/me"]


def test_a_revoked_login_is_expired(tmp_path):
    with FakeWorkIt() as fake:
        client = logged_in(fake, tmp_path)
        fake.revoke()

        with pytest.raises(LoginExpired):
            client.me()


def test_no_login(tmp_path):
    with FakeWorkIt() as fake, pytest.raises(NotLoggedIn):
        WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain).me()


def test_workit_down_is_unreachable(tmp_path):
    with FakeWorkIt() as fake:
        client = logged_in(fake, tmp_path)
        fake.stop()

        with pytest.raises(Unreachable):
            client.me()


def test_the_supabase_project_is_the_one_the_extension_uses():
    """Apply signs in to the same Supabase project as the web app and the extension (public values)."""
    config = (CODE.parent / "autofiller_extension/src/shared/config.js").read_text()
    assert re.search(r'SUPABASE_URL = "([^"]+)"', config)[1] == workit.LIVE.auth
    assert re.search(r'SUPABASE_ANON_KEY =\s*"([^"]+)"', config)[1] == workit.LIVE.anon_key
    assert re.search(r'web: "([^"]+)", api: "([^"]+)"', config).groups() == (workit.LIVE.web, workit.LIVE.api)


def test_requests_name_apply_not_python(tmp_path):
    """Cloudflare, in front of WorkIt's API, refuses Python-urllib's user agent (error 1010, seen live 2026-11-02)."""
    with FakeWorkIt() as fake:
        logged_in(fake, tmp_path).me()
        agents = {r.headers.get("user-agent", "") for r in fake.requests}
    assert agents and not any(a.startswith("Python-urllib") for a in agents)


def test_sign_out_ends_the_session_at_supabase_and_forgets_it_here(tmp_path):
    """Fault: a sign-out that leaves the refresh token in the keychain, or the session alive at Supabase."""
    with FakeWorkIt() as fake:
        client = logged_in(fake, tmp_path)
        client.me()
        client.sign_out()
        assert "/auth/v1/logout?scope=local" in [r.path for r in fake.requests]
        assert not client.logged_in() and fake.keychain.password(fake.site.auth) is None
        with pytest.raises(NotLoggedIn):
            client.me()
