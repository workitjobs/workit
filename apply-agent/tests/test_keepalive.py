"""A held form's job-site session (KAN-776): kept alive while held, and told at once when it ends.

No browser (CI's fast list): the allowlist, the words of an ended session, and the Keeper's turns on a fake page.
CDP (Playwright's Chromium, skipped without it): a fake Oracle Recruiting form held for Lisul, whose session dialog
gets only its stay-signed-in press, and whose expiry toast is told; the ping on a loopback page.
Plain (Chrome for Testing, skipped without it): the same press and ping on a plain Worker.
The submit guard's hostile session dialogs are in tests/test_submit_guard_hostile.py.
"""

import http.server
import re
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from apply import keepalive
from apply.keepalive import ENDED, Keeper, Site, site_of
from apply.submit_guard import guard, lift

ORACLE = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/210773869/apply/section/3"


# --- no browser

@pytest.mark.parametrize("url,name", [
    (ORACLE, "Oracle Recruiting"),
    ("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/X/apply/applyManually", "Workday"),
    ("https://account.amazon.jobs/en-US/applicant", "Amazon"),
    ("https://acme.eightfold.ai/careers/apply?pid=1", "Eightfold"),
    ("https://apply.careers.microsoft.com/careers/job/1", "Eightfold"),
])
def test_each_listed_site_is_found_by_its_host(url, name):
    assert site_of(url).name == name


@pytest.mark.parametrize("url", ["https://job-boards.greenhouse.io/acme/jobs/1", "https://oraclecloud.com.evil.example/x",
                                 "https://evil-myworkdayjobs.com/apply", "not a url"])
def test_a_site_off_the_list_gets_no_keep_alive_action(url):
    assert site_of(url) is None


@pytest.mark.parametrize("said", ["For security reasons your session was ended due to inactivity",
                                  "Your session has expired. Please sign in again.", "Session expired",
                                  "Your session timed out", "You have been signed out due to inactivity",
                                  "We logged you out after 20 minutes of inactivity"])
def test_the_words_of_an_ended_session(said):
    assert ENDED.search(said)


@pytest.mark.parametrize("said", ["Your session is about to expire", "Your session will expire in 2 minutes",
                                  "Sessions end after 30 minutes of inactivity", "Sign in to continue your application"])
def test_a_warning_or_a_rule_is_no_ended_session(said):
    assert not ENDED.search(said)


def test_the_warning_words_of_a_session_dialog():
    warns = re.compile(keepalive.WARNS, re.IGNORECASE)
    for said in ("Your session is about to expire", "Your session will expire in 2 minutes", "Are you still there?",
                 "For your security, your session will time out soon"):
        assert warns.search(said), said
    assert not warns.search("Submit your application")


def test_no_listed_stay_name_sends():
    assert not [name for site in keepalive.SITES for name in site.stay if keepalive.SENDS.search(name)]


class FakePage:
    """A held page as the Keeper reads it: what each LOOK says, in turn (the last one stays)."""

    plain = False

    def __init__(self, url: str, looks: list[dict]):
        self.url, self.looks, self.evaluated, self.got = url, list(looks), [], []
        self.context = SimpleNamespace(request=SimpleNamespace(get=self._get))

    def _get(self, url, **options):
        self.got.append(url)
        return SimpleNamespace(dispose=lambda: None)

    def evaluate(self, expression, arg=None):
        self.evaluated.append(expression)
        if expression == keepalive.LOOK:
            return self.looks.pop(0) if len(self.looks) > 1 else self.looks[0]
        return True

    def get_by_role(self, role, **options):
        return SimpleNamespace(all=list)


QUIET, ENDED_NOW, WARNED = {"warned": False, "ended": False}, {"warned": False, "ended": True}, {"warned": True, "ended": False}


def keeper(clock: list[float], company="JPMorgan Chase"):
    lost, lines = [], []
    return Keeper(company, lost.append, lines.append, clock=lambda: clock[0],
                  now=lambda: datetime(2026, 11, 10, 10, 42)), lost, lines


def test_an_ended_session_is_told_once_with_what_to_do():
    clock = [0.0]
    keep, lost, lines = keeper(clock)
    page = FakePage(ORACLE, [QUIET, ENDED_NOW])
    for _ in range(4):
        keep.tick(page)
        clock[0] += keepalive.LOOK_S
    assert lost == ["JPMorgan Chase's session ended; press Fill again after signing in"]
    assert keep.over
    assert lines == ["Held since 10:42; Apply keeps Oracle Recruiting's session alive; its idle limit isn't known"]


def test_words_shown_from_the_start_are_no_new_end():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage("https://acme.wd5.myworkdayjobs.com/en-US/careers/login", [ENDED_NOW, ENDED_NOW, QUIET, ENDED_NOW])
    for _ in range(3):
        keep.tick(page)
        clock[0] += keepalive.LOOK_S
    assert lost == []
    keep.tick(page)
    assert lost == ["JPMorgan Chase's session ended; press Fill again after signing in"]


def test_leaving_the_form_is_an_ended_session():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage(ORACLE, [QUIET])
    keep.tick(page)
    page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/requisitions"
    clock[0] += keepalive.LOOK_S
    keep.tick(page)
    assert lost and keep.over


def test_a_page_held_off_the_form_is_not_ended_by_leaving_it():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage("https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/1", [QUIET])
    keep.tick(page)
    page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/1/apply/email"
    clock[0] += keepalive.LOOK_S
    keep.tick(page)
    assert lost == []


def test_a_listed_site_is_pinged_at_its_interval_only():
    clock = [0.0]
    keep, _, _ = keeper(clock)
    page = FakePage(ORACLE, [QUIET])
    while clock[0] < keepalive.PING_S * 2 + 1:
        keep.tick(page)
        clock[0] += 1
    assert page.got == [ORACLE, ORACLE]
    assert page.evaluated.count(keepalive.ACTIVITY) == 2


def test_an_unlisted_site_is_only_read():
    clock = [0.0]
    keep, lost, lines = keeper(clock)
    page = FakePage("https://job-boards.greenhouse.io/acme/jobs/1", [WARNED])
    while clock[0] < keepalive.PING_S * 2:
        keep.tick(page)
        clock[0] += 1
    assert page.got == [] and set(page.evaluated) == {keepalive.LOOK} and lost == []
    assert "Apply only watches for it" in lines[0]


def test_the_tile_says_how_long_the_site_allows_when_known():
    clock = [0.0]
    known = (Site("Oracle Recruiting", re.compile(r"oraclecloud\.com$"), ("Continue",), minutes=30),)
    lines = []
    Keeper("JPMorgan Chase", lambda why: None, lines.append, sites=known, clock=lambda: clock[0],
           now=lambda: datetime(2026, 11, 10, 9, 5)).tick(FakePage(ORACLE, [QUIET]))
    assert lines == ["Held since 09:05; Apply keeps Oracle Recruiting's session alive; "
                     "it signs you out after about 30 min idle"]


def test_a_keeper_does_nothing_once_over():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage(ORACLE, [QUIET, ENDED_NOW])
    keep.tick(page)
    clock[0] += keepalive.LOOK_S
    keep.tick(page)
    clock[0] += keepalive.PING_S * 3
    keep.tick(page)
    assert len(lost) == 1 and page.got == []


# --- CDP: a fake Oracle form held for Lisul in Playwright's Chromium

# The fake's session: a warning dialog after `warn` ms of no activity, then the expiry toast and the job list after
# `end` ms more, unless its Continue (or a mouse move) resets it. It counts its Continue presses and any POST.
SESSION_PAGE = """<!doctype html><title>Apply</title><h1>Application</h1>
<form id=f method=post action="/acme/jobs/123/apply"><label>First name <input name=first value=Test></label>
<button id=send>Submit</button></form>
<div id=warn role=alertdialog aria-modal=true hidden><p>Your session is about to expire. Do you want to continue?</p>
<button type=button id=stay>Continue</button> <button type=button id=out>Sign Out</button></div>
<div id=toast hidden>For security reasons your session was ended due to inactivity</div>
<script>
window.stays = 0; window.outs = 0; let timer;
const reset = () => { clearTimeout(timer); document.getElementById('warn').hidden = true; timer = setTimeout(() => {
  document.getElementById('warn').hidden = false;
  timer = setTimeout(() => { document.getElementById('toast').hidden = false; history.pushState({}, '', '/hcmUI/CandidateExperience/en/sites/CX/requisitions'); }, END);
}, WARN); };
document.getElementById('stay').addEventListener('click', () => { stays++; reset(); });
document.getElementById('out').addEventListener('click', () => { outs++; });
reset();
</script>"""


def session_page(warn: int, end: int) -> str:
    return SESSION_PAGE.replace("END", str(end)).replace("WARN", str(warn))


@contextmanager
def held(html: str, url: str = ORACLE):
    from playwright.sync_api import sync_playwright

    sent = []
    with sync_playwright() as playwright:
        if not Path(playwright.chromium.executable_path).exists():
            pytest.skip("no Playwright Chromium here")
        browser = playwright.chromium.launch()
        context = browser.new_context()

        def answer(route):
            if route.request.method not in ("GET", "HEAD"):
                sent.append(route.request.url)
            route.fulfill(body=html, content_type="text/html")
        context.route(lambda u: True, answer)
        page = context.new_page()
        page.goto(url)
        guard(page)
        lift(page)  # held for Lisul: his page, unguarded
        try:
            yield page, sent
        finally:
            browser.close()


def turns(keep: Keeper, page, ms: int) -> None:
    for _ in range(ms // 250):
        keep.tick(page)
        page.wait_for_timeout(250)


def test_the_session_dialog_gets_only_its_continue_and_the_form_stays(monkeypatch):
    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    lost, lines = [], []
    with held(session_page(warn=800, end=4000)) as (page, sent):
        keep = Keeper("JPMorgan Chase", lost.append, lines.append)
        turns(keep, page, 6000)
        pressed = page.evaluate("() => [stays, outs, document.getElementById('toast').hidden]")
        assert page.url == ORACLE
    assert pressed[0] >= 1 and pressed[1:] == [0, True]
    assert lost == [] and sent == []
    assert "pressed the site's Continue" in lines[-1]


def test_an_ended_session_is_told_at_once(monkeypatch):
    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    monkeypatch.setattr(keepalive, "SITES", ())  # nothing keeps it alive: it ends
    lost = []
    with held(session_page(warn=300, end=600)) as (page, sent):
        keep = Keeper("JPMorgan Chase", lost.append)
        turns(keep, page, 3000)
    assert lost == ["JPMorgan Chase's session ended; press Fill again after signing in"]
    assert sent == []


@contextmanager
def loopback(html: str):
    """The page on 127.0.0.1 with a session cookie, for the ping (Playwright's request API reaches no route)."""
    gets = []

    class Pages(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            gets.append((self.path, self.headers.get("Cookie") or ""))
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Set-Cookie", "session=abc; Path=/")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            gets.append(("POST " + self.path, ""))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/acme/job/1/apply/section/2", gets
    finally:
        server.shutdown()
        server.server_close()


def test_the_ping_is_one_get_of_the_pages_own_url_with_its_cookie(monkeypatch):
    from playwright.sync_api import sync_playwright

    monkeypatch.setattr(keepalive, "PING_S", 0.0)
    here = (Site("Loopback", re.compile(r"^127\.0\.0\.1$"), ("Continue",), form=re.compile(r"/apply/section/\d+")),)
    with loopback("<title>Apply</title><input name=first>") as (url, gets), sync_playwright() as playwright:
        if not Path(playwright.chromium.executable_path).exists():
            pytest.skip("no Playwright Chromium here")
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url)
            gets.clear()
            Keeper("Acme", lambda why: None, sites=here).tick(page)
            assert page.input_value("input") == ""
        finally:
            browser.close()
    assert gets == [(urlsplit(url).path, "session=abc")]


# --- plain: a plain Worker on Chrome for Testing

def _plain_or_skip():
    from plain_fakes import have_chrome_for_testing
    if not have_chrome_for_testing():
        pytest.skip("needs Chrome for Testing (uv run playwright install chromium)")


def test_a_plain_worker_presses_only_continue_and_pings_its_own_url(monkeypatch):
    _plain_or_skip()
    from plain_fakes import fake_page

    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    monkeypatch.setattr(keepalive, "PING_S", 1.0)
    requests, lost, lines = [], [], []

    def handle(route):
        requests.append((route.request.method, route.request.url))
        route.fulfill(body=session_page(warn=800, end=4000), content_type="text/html")
    with fake_page(handle, url=ORACLE) as page:
        guard(page)
        lift(page)
        requests.clear()
        keep = Keeper("JPMorgan Chase", lost.append, lines.append)
        turns(keep, page, 6000)
        pressed = page.evaluate("() => [stays, outs, document.getElementById('toast').hidden]")
    assert pressed[0] >= 1 and pressed[1:] == [0, True]
    assert lost == []
    assert ("GET", ORACLE) in requests
    assert [r for r in requests if r[0] not in ("GET", "HEAD") and r[1].startswith("https://jpmc.")] == []
