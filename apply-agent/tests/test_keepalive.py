"""A held form's job-site session (KAN-776, KAN-779): kept alive while held on every site, and told at once when it ends.

No browser (CI's fast list): the site table and the generic rules, the words of a warning and of an ended session,
and the Keeper's turns on a fake page.
CDP (Playwright's Chromium, skipped without it): a fake Oracle Recruiting form held for review, whose session dialog
gets only its stay-signed-in press, and whose expiry toast is told; the session dialogs of Taleo, SuccessFactors,
iCIMS, a TAL.net-like site and unknown sites, each got only its stay press; the ping on a loopback page.
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


@pytest.mark.parametrize("url,name", [
    ("https://acme.taleo.net/careersection/2/jobapply.ftl?job=1", "Taleo"),
    ("https://career4.successfactors.com/careers?company=acme", "SuccessFactors"),
    ("https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=1", "BrassRing"),
])
def test_each_system_the_research_names_has_an_entry(url, name):
    assert site_of(url).name == name


@pytest.mark.parametrize("url", ["https://job-boards.greenhouse.io/acme/jobs/1", "https://oraclecloud.com.evil.example/x",
                                 "https://evil-myworkdayjobs.com/apply", "https://careers-acme.icims.com/jobs/1/job",
                                 "https://acme.tal.net/vx/candidate/apply/1", "http://127.0.0.1:8000/apply"])
def test_a_site_off_the_list_gets_the_generic_rules(url):
    assert site_of(url) is keepalive.ANY


@pytest.mark.parametrize("url", ["not a url", "about:blank", "file:///tmp/x.html", "chrome-extension://abc/page.html"])
def test_no_web_page_gets_any_keep_alive_action(url):
    assert site_of(url) is None


@pytest.mark.parametrize("said", ["For security reasons your session was ended due to inactivity",
                                  "Your session has expired. Please sign in again.", "Session expired",
                                  "Your session timed out", "You have been signed out due to inactivity",
                                  "We logged you out after 20 minutes of inactivity",
                                  "You have been logged out due to inactivity"])
def test_the_words_of_an_ended_session(said):
    assert ENDED.search(said)


@pytest.mark.parametrize("said", ["Your session is about to expire", "Your session will expire in 2 minutes",
                                  "Sessions end after 30 minutes of inactivity", "Sign in to continue your application",
                                  "You will be signed out due to inactivity in 2 minutes",
                                  "For your security, you'll be logged out after 20 minutes of inactivity"])
def test_a_warning_or_a_rule_is_no_ended_session(said):
    assert not ENDED.search(said)


@pytest.mark.parametrize("said", ["Your session is about to expire", "Your session will expire in 2 minutes",
                                  "Are you still there?", "For your security, your session will time out soon",
                                  "You will be signed out in 5 minutes due to inactivity", "You’ll be logged out soon",
                                  "Session Timeout Warning", "Would you like to extend your session?",
                                  "Your session is expiring", "Time remaining before the session expires: 4:59"])
def test_the_warning_words_of_a_session_dialog(said):
    assert re.search(keepalive.WARNS, said, re.IGNORECASE)


@pytest.mark.parametrize("said", ["Submit your application", "We use cookies to improve your experience",
                                  "Sessions end after 30 minutes of inactivity", "Continue to the next step"])
def test_words_that_are_no_session_warning(said):
    assert not re.search(keepalive.WARNS, said, re.IGNORECASE)


def test_no_stay_name_sends_or_leaves():
    names = keepalive.STAY_NAMES + tuple(name for site in keepalive.SITES for name in site.stay)
    assert not [name for name in names if keepalive.SENDS.search(name) or keepalive.LEAVES.search(name)]


@pytest.mark.parametrize("name", ["Sign out", "Log Out", "Logout", "Sign off", "Cancel", "Close", "End session",
                                  "No", "Yes", "OK", "Exit", "Leave", "Discard", "Withdraw application"])
def test_a_name_that_leaves_is_never_a_stay_name(name):
    assert keepalive.LEAVES.search(name) or keepalive.SENDS.search(name)


def test_a_name_that_sends_or_leaves_is_never_pressed_even_if_an_entry_lists_it():
    asked = []
    page = SimpleNamespace(get_by_role=lambda role, **options: asked.append(options["name"]) or SimpleNamespace(all=list))
    keepalive.press(page, Site("Bad", re.compile("."), ("Submit", "Sign out", "Yes", "Continue")))
    assert asked == ["Continue", "continue"]


def test_the_sites_own_keep_alive_address_is_same_origin_only():
    url = "https://acme.taleo.net/careersection/2/jobapply.ftl?job=1"
    assert keepalive._same_origin(url, "/careersection/keepalive.jss") == "https://acme.taleo.net/careersection/keepalive.jss"
    for away in ("https://evil.example/ping", "//evil.example/ping", "http://acme.taleo.net/ping"):
        assert keepalive._same_origin(url, away) == ""


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
    assert lines == ["Held since 10:42; Apply keeps Oracle Recruiting's session alive; "
                     "it signs you out after about 30 min idle"]


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


def test_an_unlisted_site_gets_the_generic_keep_alive():
    clock = [0.0]
    keep, lost, lines = keeper(clock)
    url = "https://careers-acme.icims.com/jobs/1/job"
    page = FakePage(url, [QUIET])
    while clock[0] < keepalive.PING_S * 2 + 1:
        keep.tick(page)
        clock[0] += 1
    assert page.got == [url, url] and page.evaluated.count(keepalive.ACTIVITY) == 2 and lost == []
    assert lines == ["Held since 10:42; Apply keeps the site's session alive; its idle limit isn't known"]


def test_nothing_is_done_on_another_host_than_the_held_one():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage("https://careers-acme.icims.com/jobs/1/job", [QUIET])
    keep.tick(page)
    page.url = "https://login.microsoftonline.com/common/oauth2/authorize"  # a sign-in page's host
    while clock[0] < keepalive.PING_S * 2:
        clock[0] += 1
        keep.tick(page)
    assert page.got == [] and keepalive.ACTIVITY not in page.evaluated and lost == []


def test_the_sites_own_keep_alive_address_is_pinged_with_the_page():
    clock = [0.0]
    url = "https://acme.taleo.net/careersection/2/jobapply.ftl?job=1"
    own = (Site("Taleo", re.compile(r"taleo\.net$"), ("Continue",), own="/careersection/keepalive.jss"),)
    keep = Keeper("Acme", lambda why: None, sites=own, clock=lambda: clock[0])
    page = FakePage(url, [QUIET])
    keep.tick(page)
    clock[0] = keepalive.PING_S
    keep.tick(page)
    assert page.got == [url, "https://acme.taleo.net/careersection/keepalive.jss"]


def test_a_page_sent_to_a_timeout_address_is_an_ended_session():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage("https://apply.careers.microsoft.com/careers/apply?pid=1", [QUIET])
    keep.tick(page)
    page.url = "https://apply.careers.microsoft.com/session_timeout?login_url=%2Flogin"
    clock[0] += keepalive.LOOK_S
    keep.tick(page)
    assert lost and keep.over


def test_a_page_held_on_a_timeout_address_is_no_new_end():
    clock = [0.0]
    keep, lost, _ = keeper(clock)
    page = FakePage("https://acme.example.com/session-expired", [QUIET])
    for _ in range(3):
        keep.tick(page)
        clock[0] += keepalive.LOOK_S
    assert lost == []


def test_no_web_page_is_only_read():
    clock = [0.0]
    keep, lost, lines = keeper(clock)
    page = FakePage("about:blank", [WARNED])
    while clock[0] < keepalive.PING_S * 2:
        keep.tick(page)
        clock[0] += 1
    assert page.got == [] and set(page.evaluated) == {keepalive.LOOK} and lost == []
    assert "only watches for its end" in lines[0]


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
    monkeypatch.setattr(keepalive, "press", lambda *args, **kwargs: "")  # nothing keeps it alive: it ends
    lost = []
    with held(session_page(warn=300, end=600)) as (page, sent):
        keep = Keeper("JPMorgan Chase", lost.append)
        turns(keep, page, 3000)
    assert lost == ["JPMorgan Chase's session ended; press Fill again after signing in"]
    assert sent == []


# KAN-779: each system's session dialog, by its likely shape (no wording is verified live:
# docs/research/session-timeouts.md). Each warns after `WARN` ms with no stay press and ends `END` ms later; its
# stay button has id=stay and its sign-out id=out. The same script as SESSION_PAGE drives it.
_SCRIPT = SESSION_PAGE[SESSION_PAGE.index("<div id=toast"):]
_FORM = """<!doctype html><title>Apply</title><h1>Application</h1>
<form id=f method=post action="/acme/jobs/123/apply"><label>First name <input name=first value=Test></label>
<button id=send>Submit</button></form>"""
SHAPES = {
    # Taleo career section: a modal whose buttons read Continue and Sign Out.
    "Taleo": ("https://acme.taleo.net/careersection/2/jobapply.ftl?job=1&lang=en",
              """<div id=warn role=dialog aria-modal=true aria-labelledby=t hidden><h2 id=t>Session Timeout</h2>
              <p>Your session will expire in 5 minutes. Do you want to continue?</p>
              <button type=button id=stay>Continue</button><button type=button id=out>Sign Out</button></div>"""),
    # SuccessFactors (SAP UI5): an alertdialog whose buttons hold their words in spans.
    "SuccessFactors": ("https://career4.successfactors.com/careers?company=acme&career_job_req_id=1",
                       """<div id=warn role=alertdialog class=sapMDialog hidden><span>Session Timeout</span>
                       <div>Your session will time out in 10 minutes. Would you like to extend your session?</div>
                       <button type=button id=stay class=sapMBtn><span><bdi>Extend Session</bdi></span></button>
                       <button type=button id=out class=sapMBtn><span><bdi>Log Out</bdi></span></button></div>"""),
    # iCIMS (no entry: the generic rules): a jQuery UI dialog asking if the applicant is still there.
    "the site": ("https://careers-acme.icims.com/jobs/1/software-intern/job?mode=apply",
                 """<div id=warn role=dialog class=ui-dialog hidden><span class=ui-dialog-title>Are you still there?</span>
                 <div>For your security, you will be logged out in 2 minutes.</div>
                 <button type=button id=stay>I'm still here</button><button type=button id=out>Log out</button></div>"""),
    # A TAL.net-like site (no entry): a native <dialog>, whose buttons are no form's.
    "a TAL.net-like site": ("https://acme.tal.net/vx/lang-en-GB/candidate/apply/1/page/2",
                            """<dialog id=warn open hidden><p>You will be signed out in 5 minutes due to inactivity.</p>
                            <button id=stay>Stay signed in</button> <button id=out>Sign out</button></dialog>"""),
    # Any other site: an aria-modal box, its stay button named in lower case.
    "an unknown site": ("https://jobs.acme-careers.example/apply/123",
                        """<div id=warn aria-modal=true hidden><p>Your session is about to expire.</p>
                        <a href="#" role=button id=stay>Keep me signed in</a> <a href="#" role=button id=out>Sign out</a></div>"""),
}


def shaped(dialog: str, warn: int = 800, end: int = 4000) -> str:
    return (_FORM + dialog + _SCRIPT).replace("END", str(end)).replace("WARN", str(warn))


@pytest.mark.parametrize("system", list(SHAPES))
def test_each_systems_session_dialog_gets_only_its_stay_press(system, monkeypatch):
    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    url, dialog = SHAPES[system]
    lost, lines = [], []
    with held(shaped(dialog), url) as (page, sent):
        keep = Keeper("Acme", lost.append, lines.append)
        turns(keep, page, 6000)
        pressed = page.evaluate("() => [stays, outs, document.getElementById('toast').hidden]")
        assert page.url.split("#")[0] == url  # an <a href="#"> stay button adds its fragment
    assert pressed[0] >= 1 and pressed[1:] == [0, True]
    assert lost == [] and sent == []
    name = system if system in ("Taleo", "SuccessFactors") else "the site"
    assert f"Apply keeps {name}'s session alive" in lines[0]
    assert "pressed the site's" in lines[-1]


def test_warning_words_with_no_dialog_role_get_no_press_and_the_end_is_told(monkeypatch):
    """A lure: the warning's words in a plain box, its Continue no dialog's. Nothing is pressed, and the end is told."""
    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    lure = """<div id=warn class=modal hidden><p>Your session is about to expire.</p>
    <button type=button id=stay>Continue</button><button type=button id=out>Sign out</button></div>"""
    lost = []
    with held(shaped(lure, warn=300, end=1500), "https://jobs.acme-careers.example/apply/123") as (page, sent):
        keep = Keeper("Acme", lost.append)
        turns(keep, page, 3000)
        pressed = page.evaluate("() => [stays, outs]")
    assert pressed == [0, 0] and sent == []
    assert lost == ["Acme's session ended; press Fill again after signing in"]


class OnePage:
    """A JobSite whose one page is already open: _Kept.open goes to the link in it."""

    def __init__(self, page):
        self.page = page

    @contextmanager
    def open(self, url, worker=0):
        self.page.goto(url)
        yield self.page


def test_a_held_form_whose_session_ends_is_told_and_fills_again(monkeypatch):
    """The hold loop runs the Keeper: the end is told while the page stays held, and Fill again still comes back."""
    from apply.rehearsal import AGAIN, _Kept

    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    monkeypatch.setattr(keepalive, "press", lambda *args, **kwargs: "")  # nothing keeps it alive: it ends
    lost = []
    with held(session_page(warn=300, end=600)) as (page, sent):
        kept = _Kept(OnePage(page), 0)
        with kept.open(ORACLE):
            release = threading.Event()
            timer = threading.Timer(20, release.set)  # the test's own end, if the hold never returns
            timer.start()
            try:
                how = kept.hold(release, keep=Keeper("JPMorgan Chase", lost.append), fill_again=lambda: bool(lost))
            finally:
                timer.cancel()
    assert how == AGAIN
    assert lost == ["JPMorgan Chase's session ended; press Fill again after signing in"]
    assert sent == []


def test_after_a_stay_press_submit_is_held_until_his_dismiss(monkeypatch):
    """KAN-776, the review of #541: after the press, the page is his but his Submit stays held, the guard whole.
    His click on Submit sends nothing; once he presses the note's Dismiss, his Submit goes through."""
    from apply.rehearsal import _Kept

    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    steps, sent_at = [], {}
    with held(session_page(warn=500, end=60_000)) as (page, sent):
        keep = Keeper("JPMorgan Chase", lambda why: None)

        def tend(page) -> None:  # Lisul, on the hold loop's own thread
            if keep.holding() and "held" not in steps:
                steps.append("held")
                page.locator("#send").click()  # his Submit while held: blocked
                page.wait_for_timeout(800)
                sent_at["held"] = list(sent)
                page.locator("#apply-rehearsal-blocked button", has_text="Dismiss").click()
            elif "held" in steps and not keep.holding() and "sent" not in steps:
                steps.append("sent")
                page.locator("#send").click()  # his Submit, his again

        kept = _Kept(OnePage(page), 0)
        with kept.open(ORACLE):
            release = threading.Event()
            timer = threading.Timer(12, release.set)
            timer.start()
            try:
                kept.hold(release, keep=keep, tend=tend)
            finally:
                timer.cancel()
    assert steps == ["held", "sent"]
    assert sent_at["held"] == []
    assert any(url.endswith("/acme/jobs/123/apply") for url in sent)


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


LOOPBACK = re.compile(r"^127\.0\.0\.1$")


@pytest.mark.parametrize("sites,also", [
    ((Site("Loopback", LOOPBACK, ("Continue",), form=re.compile(r"/apply/section/\d+")),), []),
    ((), []),  # no entry: the generic rules ping it the same
    ((Site("Loopback", LOOPBACK, ("Continue",), own="/acme/keepalive"),), ["/acme/keepalive"]),
    ((Site("Loopback", LOOPBACK, ("Continue",), own="http://localhost:9/keepalive"),), []),  # another origin: never
])
def test_the_ping_is_one_get_of_the_pages_own_url_with_its_cookie(sites, also, monkeypatch):
    from playwright.sync_api import sync_playwright

    monkeypatch.setattr(keepalive, "PING_S", 0.0)
    here = sites
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
    assert gets == [(urlsplit(url).path, "session=abc")] + [(path, "session=abc") for path in also]


# --- plain: a plain Worker on Chrome for Testing

def _plain_or_skip():
    from plain_fakes import have_chrome_for_testing
    if not have_chrome_for_testing():
        pytest.skip("needs Chrome for Testing (uv run playwright install chromium)")


@pytest.mark.parametrize("system", ["Oracle Recruiting", "a TAL.net-like site"])
def test_a_plain_worker_presses_only_the_stay_button_and_pings_its_own_url(system, monkeypatch):
    _plain_or_skip()
    from plain_fakes import fake_page

    url, html = (ORACLE, session_page(warn=800, end=4000)) if system == "Oracle Recruiting" else \
        (SHAPES[system][0], shaped(SHAPES[system][1]))
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    monkeypatch.setattr(keepalive, "LOOK_S", 0.25)
    monkeypatch.setattr(keepalive, "PING_S", 1.0)
    requests, lost, lines = [], [], []

    def handle(route):
        requests.append((route.request.method, route.request.url))
        route.fulfill(body=html, content_type="text/html")
    with fake_page(handle, url=url) as page:
        guard(page)
        lift(page)
        requests.clear()
        keep = Keeper("Acme", lost.append, lines.append)
        turns(keep, page, 6000)
        pressed = page.evaluate("() => [stays, outs, document.getElementById('toast').hidden]")
    assert pressed[0] >= 1 and pressed[1:] == [0, True]
    assert lost == []
    assert ("GET", url) in requests
    assert [r for r in requests if r[0] not in ("GET", "HEAD") and r[1].startswith(origin)] == []
