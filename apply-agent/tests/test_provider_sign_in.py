"""A provider sign-in in the way of a Claude fill form (KAN-763): Microsoft Careers' Apply now opens a window that
offers "Sign in using Google" (Microsoft, LinkedIn, Facebook). The stop there is a Needs sign-in pause, and the
rehearsal goes on by itself once the applicant has signed in on the page, with no Resume. Apply presses no
provider button and sends nothing. On the fake Microsoft Careers (tests/fake_microsoft.py); opens Chromium."""

import json
import re
from contextlib import contextmanager

import pytest
from fake_microsoft import APPLY, URL, FakeMicrosoftServer, sign_in
from fakes import FakeClaude, RecordingBoard
from test_rehearse import adapters
from test_resume import handed_pages
from test_run_answers import profile_with

from apply import provider_sign_in, rehearsal, worker
from apply.claude_fill import ClaudeFill
from apply.model import Handoff
from apply.profile import ApplicantProfile

QUESTIONS = [{"label": label, "kind": "text", "required": True, "options": []}
             for label in ("First Name", "Last Name", "Email")]
# Claude's own words on the live page (2026-11-10): only plain code's read of the page makes it a sign-in.
WHY = ('Clicking "Apply now" opens a Microsoft Careers sign-in window, and the form can\'t be reached without '
       'signing in. The window offers "Sign in using Google" (and Microsoft, LinkedIn and Facebook), so the person '
       "needs to sign in themselves.")


def microsoft_driver(page, schema: dict, prompt: str, files: list) -> dict:
    """Plays Haiku on the fake Microsoft Careers: Apply now on the posting, then the form's questions, or the stop
    at the sign-in window; a fill types each answer and names the button that sends."""
    if "questions" in schema["properties"]:
        if page.get_by_role("button", name="Apply now").is_visible():
            page.get_by_role("button", name="Apply now").click()
            page.wait_for_url(APPLY)
        if page.get_by_role("dialog").is_visible():
            return {"blocked": True, "why": WHY, "questions": []}
        return {"blocked": False, "why": "", "questions": QUESTIONS}
    fields = json.loads(re.search(r"<fields>(.*?)</fields>", prompt, re.DOTALL)[1])
    for field in fields:
        page.get_by_label(field["question"], exact=True).fill(field["answer"])
    return {"blocked": False, "why": "", "submit_button": "Submit application",
            "filled": [{"field": f["field"], "shown": [f["answer"]]} for f in fields]}


def test_the_page_reads_as_a_provider_sign_in_until_the_account_menu_shows():
    with FakeMicrosoftServer() as server, server.open(URL) as page:
        assert provider_sign_in.shows(page) == [] and not provider_sign_in.signed_in(page)  # "Sign in" in its header
        page.get_by_role("button", name="Apply now").click()
        page.wait_for_url(APPLY)
        assert provider_sign_in.shows(page) == ["Google", "Microsoft", "LinkedIn", "Facebook"]
        assert not provider_sign_in.signed_in(page)
        sign_in(page)
        assert provider_sign_in.shows(page) == [] and provider_sign_in.signed_in(page)
    assert server.provider_opened == [] and server.submissions == []


def test_a_claude_fill_stop_at_a_provider_sign_in_goes_on_by_itself_once_signed_in(monkeypatch, tmp_path):
    handed = handed_pages(monkeypatch)

    class Lisul(RecordingBoard):
        turns, paused = 0, {}

        def resumed(self, worker):
            return False  # he never presses Resume

        def answered(self, worker):  # each turn of the held page, on its own thread
            if not handed or handed[-1].is_closed():
                return []
            page, self.turns = handed[-1], self.turns + 1
            caption = self.captions[worker]
            if "Went on by itself" in " ".join(caption.get("history") or []) and caption.get("status") != "filling" \
                    or self.turns > 40:
                page.close()
            elif self.turns == 2:
                self.paused = dict(caption)
                sign_in(page)  # in the provider's own window, then the apply page reloads signed in
            return []

    board, lines = Lisul(), []
    with FakeMicrosoftServer() as server:  # provider_sign_in off: the sign-in is his (KAN-878)
        [first] = rehearsal.rehearse([URL], adapters(server, FakeClaude(driver=microsoft_driver), board=board),
                                     ApplicantProfile.load(profile_with(tmp_path, {"provider_sign_in": "off"})), 1,
                                     keep_open=True, out=lines.append)

    # Paused as a sign-in, not as Claude's free-text handoff, with Resume offered.
    assert first.outcome == rehearsal.SIGN_IN and "asks you to sign in (Google, Microsoft, LinkedIn, Facebook)" in first.why
    assert board.paused["status"] == rehearsal.SIGN_IN and board.paused["resume"] == {"ok": True}
    history = board.captions[0]["history"]
    assert [h.split(" ", 1)[1].split(":")[0] for h in history][:2] == ["Paused", "Went on by itself"], history
    # With no Resume, the form was read again and filled to its last page; nothing pressed a provider or sent it.
    assert board.captions[0]["status"] == "ready to submit", board.captions[0].get("why")
    assert server.provider_opened == [] and server.submissions == []
    assert len({id(page) for page in handed}) <= 2


def test_a_claude_fill_stop_with_no_provider_sign_in_keeps_no_signed_in_check():
    class Said:
        def drive(self, **_):
            raise AssertionError("not driven")

    fill = ClaudeFill(Said())
    assert fill.signed_in is None and worker.ResumeCheck(fill).signed_in is None
    fill._at_provider = True  # the last drive stopped at a provider sign-in
    assert worker.ResumeCheck(fill).signed_in is provider_sign_in.signed_in


# --- Sign in with Google by plain code (KAN-878)

ACCOUNT = "test.person@example.com"


@contextmanager
def _at_sign_in(server):
    """The fake's apply page at its sign-in window, under the drive guard, as Claude fill leaves it."""
    from apply.submit_guard import DriveGuard

    with server.open(URL) as page:
        page.get_by_role("button", name="Apply now").click()
        page.wait_for_url(APPLY)
        yield page, DriveGuard(page)


def test_a_google_sign_in_picks_the_applicants_account_and_comes_back_signed_in():
    # Fault: the Google button not pressed, the chooser's pick missed in the window it opened, or anything typed into
    # Google's pages.
    server = FakeMicrosoftServer(google="chooser", account=ACCOUNT)
    with _at_sign_in(server) as (page, guard):
        provider_sign_in.with_google(page, ACCOUNT, "Microsoft", guard, wait=15)
        assert provider_sign_in.signed_in(page)
    assert server.provider_opened == ["/oauth/google"] and server.picked == [ACCOUNT]
    assert server.typed == [] and server.submissions == []


@pytest.mark.parametrize(("google", "said"), [("password", "a password"), ("passkey", "a passkey"),
                                              ("rejected", "may not be secure")])
def test_a_google_page_that_asks_for_more_than_the_pick_is_the_applicants(google, said):
    # Fault: Apply waiting out a Google page it must never answer, or typing into it.
    server = FakeMicrosoftServer(google=google, account=ACCOUNT)
    with _at_sign_in(server) as (page, guard), pytest.raises(Handoff, match=f"^Needs sign-in: .*{said}"):
        provider_sign_in.with_google(page, ACCOUNT, "Microsoft", guard, wait=15)
    assert server.typed == [] and server.submissions == []


def test_a_claude_fill_form_behind_a_google_sign_in_is_signed_in_and_filled_with_no_pause(tmp_path):
    # Fault (KAN-878): the policy's Google sign-in never tried, so the form waits for the applicant as before, or
    # tried and the fill not driven again from the signed-in page.
    profile = ApplicantProfile.load(profile_with(tmp_path))
    login = profile.get("identity.email")
    with FakeMicrosoftServer(google="chooser", account=login) as server:
        [done] = rehearsal.rehearse([URL], adapters(server, FakeClaude(driver=microsoft_driver)), profile, 1,
                                    keep_open=False, out=lambda line: None)
    assert done.outcome == "ready to submit", done.why
    assert server.provider_opened == ["/oauth/google"] and server.picked == [login]
    assert server.typed == [] and server.submissions == []


@pytest.mark.parametrize(("google", "scope", "said"), [
    ("chooser", "openid email https://www.googleapis.com/auth/drive", "asks Google for more than your name and email"),
    ("chooser", "", "didn't say what it asks Google for"),
    ("granted", "openid email", "didn't say what it asks Google for"),
    ("consent", "openid email profile", "Google asks you to let"),
    ("straight", "openid email profile", "Google asks you to let")])
def test_a_google_sign_in_that_asks_for_more_than_name_and_email_or_says_nothing_is_the_applicants(google, scope, said):
    # Fault (KAN-878's review, two rounds): a page's Google button opened another app's OAuth request (Drive), with
    # its scopes in the URL, hidden by a redirect straight to Google's consent, or added by the app's earlier grants,
    # and Apply picked the account or pressed Continue on Google's consent.
    server = FakeMicrosoftServer(google=google, account=ACCOUNT, scope=scope)
    with _at_sign_in(server) as (page, guard), pytest.raises(Handoff, match=said):
        provider_sign_in.with_google(page, ACCOUNT, "Microsoft", guard, wait=15)
    # The account is picked only on a chooser that asked for a sign-in alone; Google's Continue is never pressed.
    assert server.picked == ([ACCOUNT] if google == "consent" else []) and server.typed == []


def test_a_google_button_that_would_submit_a_form_is_never_pressed():
    # Fault (KAN-878's review): Eightfold's Google class on a wrapper of the form's submit button, or on a label for
    # it, pressed as Sign in with Google.
    from fake_microsoft import (
        FakeMicrosoftServer as _Server,  # noqa: F401 (the same browser setup)
    )
    from playwright.sync_api import sync_playwright

    pages = ['<form><div class="candidateAuthGoogleLoginButton"><button>Sign in with Google</button></div></form>',
             '<form><button id=s hidden>Submit</button></form><label class="candidateAuthGoogleLoginButton" for=s>'
             "Sign in with Google</label>"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for html in pages:
            page = browser.new_page()
            page.set_content(html)
            with pytest.raises(Handoff, match="would submit a form"):
                provider_sign_in.with_google(page, ACCOUNT, "Example", None, wait=2)
        browser.close()


def test_a_mailed_password_reset_link_is_never_opened():
    # Fault (KAN-878's review): on a reopened form, now signing in, Claude pressed Forgot password and called the page
    # "link sent", and Apply opened the newest mail from the site: the reset's link.
    from types import SimpleNamespace

    from apply.account_pages import AccountPages

    opened = []
    accounts = SimpleNamespace(login=ACCOUNT, link=lambda *a: "https://acme.example/reset-password?token=1")
    pages = AccountPages(accounts, {})
    page = SimpleNamespace(goto=opened.append)
    with pytest.raises(Handoff, match="password reset, and Apply never opens one"):
        pages._link(page, "acme.example", None, "https://acme.example/jobs/1")
    assert opened == []


def test_a_scope_nested_redirects_deep_is_still_read():
    # Fault (KAN-878's review): scopes() decoded a fixed four times and searched only the first three, so a Drive
    # request three redirects deep under a chooser that showed "openid" read as a sign-in alone.
    from urllib.parse import quote

    deep = "https://accounts.google.com/o/oauth2/v2/auth?scope=" + quote("openid https://www.googleapis.com/auth/drive")
    for _ in range(5):
        deep = "https://accounts.google.com/ServiceLogin?continue=" + quote(deep, safe="")
    url = "https://accounts.google.com/v3/signin/accountchooser?scope=openid&continue=" + quote(deep, safe="")
    assert "https://www.googleapis.com/auth/drive" in provider_sign_in.scopes(url)



def test_a_scope_written_in_another_case_or_after_a_semicolon_is_read():
    # Fault (round 4 of KAN-878's review): "Scope=" or ";scope=" read as no scope at all.
    for url in ("https://accounts.google.com/x?Scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive",
                "https://accounts.google.com/x?a=1;scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive"):
        assert provider_sign_in.scopes(url) == {"https://www.googleapis.com/auth/drive"}
