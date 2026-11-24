"""The Apply window's Accounts tab (KAN-591): each Employer account Apply made, with Show password, Copy password
and Open sign-in page, and the password Lisul chooses for every new account (KAN-838). Passwords are in Keychain (a
fake one here); one goes to the window only when he presses Show password or Copy password, and the window writes a
copied one to the clipboard itself (D35). Needs no browser."""

import json
import urllib.error
import urllib.request
from datetime import date
from types import SimpleNamespace

import pytest

from apply.accounts import RULE
from apply.accounts_tab import AccountsTab
from apply.chrome_finder import NO_CHROME
from apply.dashboard import Dashboard, NoFrames
from apply.keychain import CHOSEN, InMemoryKeychain
from apply.tracker import EmployerAccount

ASML = EmployerAccount("ASML", "asml.wd3.myworkdayjobs.com", "lisul@example.com", date(2026, 11, 2))
KLA = EmployerAccount("KLA", "wd5.myworkdaysite.com/kla", "lisul@example.com", date(2026, 11, 3))
PASSWORD = "Fake-Keychain-Pw-7x!Q"  # a made-up password in a fake Keychain: never a real one


def call(board, path, body=None, token=None, origin=None):
    """(status, JSON reply) of one request to the window's server, as the page sends it."""
    headers = {"X-Apply-Token": board.token if token is None else token}
    if origin:
        headers["Origin"] = origin
    data = None if body is None else json.dumps(body).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(board.url + path, data, headers)) as reply:
            return reply.status, reply.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def window(tab):
    return Dashboard(0, NoFrames(), accounts=tab)


def test_the_tab_lists_every_employer_account_apply_made():
    tab = AccountsTab(lambda: [ASML, KLA], InMemoryKeychain({ASML.site: PASSWORD}))
    with window(tab) as board:
        status, body = call(board, "/accounts")

    assert status == 200
    assert [(a["company"], a["site"], a["login"], a["created"]) for a in json.loads(body)["accounts"]] == [
        ("KLA", "wd5.myworkdaysite.com/kla", "lisul@example.com", "2026-11-03"),
        ("ASML", "asml.wd3.myworkdayjobs.com", "lisul@example.com", "2026-11-02"),
    ]  # newest first
    assert PASSWORD not in body


def test_the_view_says_whether_lisul_chose_a_password_and_gives_the_rule_never_the_password():
    for keychain, chosen in ((InMemoryKeychain(), False), (InMemoryKeychain({CHOSEN: "Fake!Chosen7xQ"}), True)):
        with window(AccountsTab(lambda: [ASML], keychain)) as board:
            _, body = call(board, "/accounts")
        view = json.loads(body)
        assert (view["chosen"], view["rule"]) == (chosen, RULE)
        assert "Fake!Chosen7xQ" not in body


def test_only_the_window_may_list_them():
    tab = AccountsTab(lambda: [ASML], InMemoryKeychain())
    with window(tab) as board:
        assert call(board, "/accounts", token="guessed")[0] == 403
        assert call(board, "/accounts", origin="https://evil.example")[0] == 403


def test_copy_password_is_the_windows_own_clipboard_write_of_the_shown_password():
    # D35: no clipboard code in Apply. The page asks for the password as Show password does, and writes it with
    # navigator.clipboard, as the window's other copy buttons do; no route copies, and nothing clears it later.
    tab = AccountsTab(lambda: [ASML], InMemoryKeychain({ASML.site: PASSWORD}))
    with window(tab) as board:
        page = board.page()
        status, body = call(board, "/accounts/copy", {"site": ASML.site})

    assert "navigator.clipboard.write([new ClipboardItem(" in page  # started inside the click, as WebKit needs
    assert "post('/accounts/show', {site: account.site})" in page
    assert status == 404 and PASSWORD not in body


ASML_POSTING = "https://asml.wd3.myworkdayjobs.com/en-US/ASMLExternal/job/US-Wilton/Intern_R12345"
KLA_POSTING = "https://wd5.myworkdaysite.com/recruiting/kla/Search/job/Milpitas/Intern_R1"


def opening(rows):
    opened = []
    tab = AccountsTab(lambda: [ASML, KLA], InMemoryKeychain(), rows=lambda: rows, everyday=opened.append)
    return tab, opened


def test_open_sign_in_page_opens_the_accounts_posting_in_lisuls_own_chrome():
    # Workday's job page has Sign In in its header; the tenant alone names no site path.
    rows = [SimpleNamespace(posting_url="https://boards.greenhouse.io/stripe/jobs/1"),
            SimpleNamespace(posting_url=KLA_POSTING), SimpleNamespace(posting_url=ASML_POSTING)]
    tab, opened = opening(rows)
    with window(tab) as board:
        status, body = call(board, "/accounts/open", {"site": ASML.site})
        call(board, "/accounts/open", {"site": KLA.site})

    assert status == 200
    assert "your Chrome" in json.loads(body)["message"]
    assert opened == [ASML_POSTING, KLA_POSTING]


def test_an_account_with_no_posting_in_the_tracker_opens_its_site():
    tab, opened = opening([])
    with window(tab) as board:
        call(board, "/accounts/open", {"site": KLA.site})

    assert opened == ["https://wd5.myworkdaysite.com/"]


def test_only_the_window_may_open_a_sign_in_page_and_only_for_a_listed_account():
    tab, opened = opening([SimpleNamespace(posting_url=ASML_POSTING)])
    with window(tab) as board:
        assert call(board, "/accounts/open", {"site": ASML.site}, token="guessed")[0] == 403
        assert call(board, "/accounts/open", {"site": ASML.site}, origin="https://evil.example")[0] == 403
        assert call(board, "/accounts/open", {"site": "evil.example"})[0] == 404

    assert opened == []


def test_open_sign_in_page_with_no_chrome_says_how_to_get_it():
    def no_chrome(url):
        raise FileNotFoundError(NO_CHROME)

    tab = AccountsTab(lambda: [ASML], InMemoryKeychain(), everyday=no_chrome)
    with window(tab) as board:
        status, body = call(board, "/accounts/open", {"site": ASML.site})

    assert (status, json.loads(body)) == (404, {"error": NO_CHROME})


def showing(passwords=None):
    """A tab over a fake Keychain that holds ASML's password."""
    return AccountsTab(lambda: [ASML], InMemoryKeychain({ASML.site: PASSWORD} if passwords is None else passwords))


def test_show_password_sends_the_listed_accounts_password_to_the_window_and_prints_none(capsys):
    with window(showing()) as board:
        page = board.page()
        status, body = call(board, "/accounts/show", {"site": ASML.site})

    assert (status, json.loads(body)) == (200, {"password": PASSWORD})
    printed = capsys.readouterr()
    for kept in (page, printed.out, printed.err):  # in no page until pressed, and in no printed line
        assert PASSWORD not in kept


@pytest.mark.parametrize("token, origin", [("guessed", None), (None, "https://evil.example")])
def test_only_the_window_may_show_a_password(token, origin):
    with window(showing()) as board:
        status, body = call(board, "/accounts/show", {"site": ASML.site}, token=token, origin=origin)

    assert status == 403 and PASSWORD not in body


def test_a_site_apply_did_not_list_is_never_shown():
    with window(showing({ASML.site: PASSWORD, "evil.wd1.myworkdayjobs.com": PASSWORD, CHOSEN: PASSWORD})) as board:
        for site in ("evil.wd1.myworkdayjobs.com", CHOSEN):
            status, body = call(board, "/accounts/show", {"site": site})
            assert status == 404 and PASSWORD not in body


def test_an_account_keychain_has_no_password_for_says_so():
    with window(showing(passwords={})) as board:
        status, body = call(board, "/accounts/show", {"site": ASML.site})

    assert status == 404
    assert "Keychain has no password" in json.loads(body)["error"]


def test_the_password_lisul_chooses_is_saved_for_new_accounts_and_never_printed(capsys):
    keychain = InMemoryKeychain()
    with window(AccountsTab(lambda: [ASML], keychain)) as board:
        status, body = call(board, "/accounts/password", {"password": "Fake!Chosen7xQ"})
        assert json.loads(call(board, "/accounts")[1])["chosen"] is True

    assert status == 200 and "Apply uses this password for each new account" in json.loads(body)["message"]
    assert keychain.password(CHOSEN) == "Fake!Chosen7xQ"
    printed = capsys.readouterr()
    assert "Fake!Chosen7xQ" not in printed.out + printed.err + body


def test_changing_the_chosen_password_keeps_each_accounts_own():
    keychain = InMemoryKeychain({CHOSEN: "Fake!Chosen7xQ", ASML.site: "Fake!Chosen7xQ"})
    with window(AccountsTab(lambda: [ASML], keychain)) as board:
        assert call(board, "/accounts/password", {"password": "Fake@Changed9yR"})[0] == 200

    assert keychain.password(CHOSEN) == "Fake@Changed9yR" and keychain.password(ASML.site) == "Fake!Chosen7xQ"


@pytest.mark.parametrize("password", ["short1!A", "no-dash-allowed-1A", 12345678901234])
def test_a_chosen_password_that_breaks_the_rule_is_refused_and_not_saved(password):
    keychain = InMemoryKeychain()
    with window(AccountsTab(lambda: [ASML], keychain)) as board:
        status, body = call(board, "/accounts/password", {"password": password})

    assert status == 400 and keychain.password(CHOSEN) is None
    assert json.loads(body)["error"] in (f"Use {RULE}.", "Not a password.")


@pytest.mark.parametrize("token, origin", [("guessed", None), (None, "https://evil.example")])
def test_only_the_window_may_choose_the_password(token, origin):
    keychain = InMemoryKeychain()
    with window(AccountsTab(lambda: [ASML], keychain)) as board:
        status, _ = call(board, "/accounts/password", {"password": "Fake!Chosen7xQ"}, token=token, origin=origin)

    assert status == 403 and keychain.password(CHOSEN) is None
