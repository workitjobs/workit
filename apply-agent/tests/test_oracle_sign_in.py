"""Seam 1 for Oracle's sign-in: whole `apply run`s on a saved Oracle posting
(real up to its email step; tests/fake_oracle.py), with a fake mailbox. Oracle
has no Filler, so once signed in by plain code (its emailed one-time code,
zero tokens) Claude fill fills the form; FakeClaude's
OracleDriver plays Haiku there."""

import json
import re
import time
from datetime import timedelta

import pytest
from conftest import FIXTURES, FORMS
from fake_oracle import FakeOracleServer
from fakes import FakeClaude
from test_employer_accounts import NOW, World
from test_matches import feed_record

from apply.model import Handoff

MACYS_FORM = FORMS / "oracle-macys"
MACYS_URL = "https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/91780"
QUESTIONS = [
    {"label": "First Name", "kind": "text", "required": True, "options": []},
    {"label": "Last Name", "kind": "text", "required": True, "options": []},
    {"label": "Phone Number", "kind": "text", "required": True, "options": []},
    # Locked once signed in, as Oracle locks it: a fill of it failed, and every other field of the batch with it.
    {"label": "Email Address", "kind": "text", "required": True, "options": []},
    {"label": "Resume", "kind": "file", "required": True, "options": []},
]


def oracle_driver(page, schema: dict, prompt: str, files: list) -> dict:
    """Plays Haiku on the fake Oracle form, already signed in to."""
    if "questions" in schema["properties"]:
        return {"blocked": False, "why": "", "questions": QUESTIONS}
    fields = json.loads(re.search(r"<fields>(.*?)</fields>", prompt, re.DOTALL)[1])
    by_name = {f.name: f for f in files}
    for field in fields:
        if field["answer"] in by_name:
            page.locator("input[type=file]").set_input_files(by_name[field["answer"]])
        else:
            page.get_by_label(field["question"], exact=True).fill(field["answer"])
    return {"blocked": False, "why": "", "submit_button": "Submit",
            "filled": [{"field": f["field"], "shown": [f["answer"]]} for f in fields]}


def names_no_submit(page, schema: dict, prompt: str, files: list) -> dict:
    """Plays Haiku as it filled BGC's Oracle form (live 2026-11-27): every field, and no button that sends named."""
    said = oracle_driver(page, schema, prompt, files)
    return said if "questions" in schema["properties"] else said | {"submit_button": "", "next_button": ""}


def macys() -> dict:
    return feed_record(id="macys", company_name="Macy's", title="Software Engineer Intern", url=MACYS_URL)


def run(world: World, server: FakeOracleServer, claude: FakeClaude):
    world.claude = claude
    [row] = world.run(server, macys())
    return row


def test_an_oracle_posting_is_signed_in_to_with_the_code_mailed_to_gmail_then_filled_and_submitted():
    world = World()
    claude = FakeClaude(driver=oracle_driver)

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox) as server:
        row = run(world, server, claude)

    assert (row.status, row.job_system) == ("submitted", "oracle")
    assert row.reason.startswith("Claude fill: 2 sessions")  # it drove only once signed in
    [email_step] = server.emails
    assert (email_step["email"], email_step["accepted"], email_step["honeypot"]) == ("test.person@example.com", True, "")
    assert server.tried_codes == server.codes_sent  # the code from Gmail, typed once
    [sent] = server.submissions
    assert sent.application["first-name"] == "Test"
    asked = [f["question"] for p in claude.prompts if "<fields>" in p
             for f in json.loads(re.search(r"<fields>(.*?)</fields>", p, re.DOTALL)[1])]
    assert "Email Address" not in asked and "Phone Number" in asked  # shown already, and locked
    assert sent.files["resume"] == (FIXTURES / "one-pager.pdf").read_bytes()
    assert world.tracker.employer_accounts() == []  # an emailed code is not an account


def test_oracles_own_submit_ends_the_fill_when_claude_names_no_button_that_sends():
    world = World()

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox) as server:
        row = run(world, server, FakeClaude(driver=names_no_submit))

    assert row.status == "submitted", row.reason  # never "can't tell this is the form's last page"
    [sent] = server.submissions
    assert sent.application["first-name"] == "Test"


def test_a_returning_candidate_confirms_their_last_name_before_the_code():
    world = World()

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox, returning=True) as server:
        row = run(world, server, FakeClaude(driver=oracle_driver))

    assert row.status == "submitted"
    assert len(server.tried_codes) == 1


def test_a_first_time_candidate_oracle_asks_no_code_of_goes_straight_to_the_form():
    world = World()

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox, verify=None) as server:
        row = run(world, server, FakeClaude(driver=oracle_driver))

    assert row.status == "submitted"
    assert world.mailbox.looks == 0


def test_a_code_sent_by_text_message_is_a_handoff_before_claude_spends_a_token():
    world = World()
    claude = FakeClaude(driver=oracle_driver)

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox, verify="sms") as server:
        row = run(world, server, claude)

    assert row.status == "handoff"
    assert "text message" in row.reason
    assert claude.asked == [] and server.submissions == []


def test_a_code_missing_after_about_two_minutes_needs_lisul_and_send_new_code_is_never_clicked():
    world = World()
    claude = FakeClaude(driver=oracle_driver)

    with FakeOracleServer(MACYS_FORM, mailbox=world.mailbox, codes_lost=True) as server:
        row = run(world, server, claude)

    assert row.status == "handoff"
    assert "Type the emailed code: no verification code" in row.reason
    assert server.resends == 0
    assert world.clock.now() - NOW >= timedelta(minutes=2)
    assert server.tried_codes == [] and claude.asked == []


def test_the_cookie_banner_over_the_email_step_is_declined_before_next():
    # American Express's Oracle site (seen live): the banner took the click on Next, and sign-in timed out.
    from playwright.sync_api import sync_playwright

    from apply import oracle

    banner = ('<div class="cookie-consent-modal" style="position:fixed;inset:0;background:#fff">Our Use of Cookies'
              '<button onclick="this.parentElement.style.display=\'none\'">Reject All</button><button>Accept All</button></div>'
              '<button onclick="document.title=\'next\'">Next</button>')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(banner)
        oracle._decline_cookies(page)
        page.get_by_role("button", name="Next").click(timeout=2000)
        assert page.title() == "next"
        browser.close()


# Emerson's OneTrust banner (live 2026-11-27): no Reject All, a dark filter over the page, and its settings' Confirm My
# Choices keeps only the necessary cookies.
ONETRUST = """<div id="onetrust-consent-sdk"><div class="onetrust-pc-dark-filter"
  style="position:fixed;inset:0;z-index:2147483645;background:rgba(0,0,0,.5)"></div>
<div id="onetrust-banner-sdk" style="position:fixed;top:0;left:0;right:0;z-index:2147483646;background:#fff">
  By clicking "Accept All Cookies", you agree to the storing of cookies on your device.
  <button id="onetrust-pc-btn-handler" onclick="document.getElementById('onetrust-pc-sdk').style.display='block'">
    Cookies Settings</button><button id="onetrust-accept-btn-handler">Accept All Cookies</button></div>
<div id="onetrust-pc-sdk" style="display:none;position:fixed;bottom:0;z-index:2147483647;background:#fff">
  <button class="save-preference-btn-handler" onclick="document.getElementById('onetrust-consent-sdk').remove();
    document.title = 'necessary only'">Confirm My Choices</button></div></div>
<button onclick="document.title += ', applied'">Apply Now</button>"""


def test_a_onetrust_banner_with_no_reject_keeps_only_the_necessary_cookies_before_apply():
    from playwright.sync_api import sync_playwright

    from apply import oracle

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(ONETRUST)
        oracle._decline_cookies(page)
        page.get_by_role("button", name="Apply Now").click(timeout=2000)
        assert page.title() == "necessary only, applied"
        browser.close()


def test_an_apply_button_still_covered_is_a_handoff_not_a_timeout(monkeypatch):
    from playwright.sync_api import sync_playwright

    from apply import oracle

    monkeypatch.setattr(oracle, "TIMEOUT", 2.0)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(1000)
        page.set_content('<div style="position:fixed;inset:0;z-index:9"></div><button>Apply Now</button>')
        with pytest.raises(Handoff, match="covers its Apply button"):
            oracle.sign_in(page, None, "Doe", True)
        browser.close()


POSTING = "https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1"


def _posting_whose_apply_goes_to(page, where: str,
                                 shows: str = "<h1>Continue your application</h1><button>Continue</button>") -> None:
    """A posting whose Apply Now goes to `where`, a path under it, which `shows` a page of its own."""
    page.route("**/*", lambda route: route.fulfill(content_type="text/html", body=(
        "<h1>Software Engineering Intern</h1><button onclick=\"location.href = location.href + '%s'\">Apply Now</button>"
        % where if route.request.url == POSTING else shows)))
    page.goto(POSTING)


# The form of a draft an earlier attempt held, as Emerson's showed it at .../apply/email (live 2026-11-27).
DRAFT_FORM = ('<h1>Job application form</h1><div class="apply-flow-block"><h2>Contact Information</h2>'
              '<input name="lastName" value="Person"></div><div class="apply-flow-block"><h2>Supporting Documents</h2>'
              '</div><button class="apply-flow-pagination__submit-button">Submit</button>')


def test_an_apply_that_opens_the_form_of_an_earlier_draft_at_its_email_path_needs_no_email_step(monkeypatch):
    """Emerson's refill (live 2026-11-27): Apply opened the held draft's form at .../apply/email, with no email box."""
    from playwright.sync_api import sync_playwright

    from apply import oracle

    monkeypatch.setattr(oracle, "TIMEOUT", 3.0)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        _posting_whose_apply_goes_to(page, "/apply/email", DRAFT_FORM)
        oracle.sign_in(page, None, "Doe", True)
        assert page.url.endswith("/apply/email") and oracle.signed_in(page)
        page.goto(POSTING + "/apply/email")  # Resume on that form: no Apply to press, and nothing waited for
        oracle.sign_in(page, None, "Doe", True)
        browser.close()


# The email step in phone mode, as Oracle shows it to a candidate it last reached by phone (Emerson's, live
# 2026-11-27): the email box shows only once its switch is pressed.
PHONE_MODE = """document.addEventListener('DOMContentLoaded', () => {
  document.head.insertAdjacentHTML('beforeend', '<style>body:not(.by-email) input[type=email] {display: none}</style>');
  const shown = setInterval(() => {
    const email = document.querySelector('input[type=email]');
    if (!email) return;
    clearInterval(shown);
    email.insertAdjacentHTML('beforebegin', '<button type="button" id="applyFlowVerifyEmail" '
      + 'class="quick-apply-flow-verify-method__button">Do you want to communicate by email instead?</button>');
    document.getElementById('applyFlowVerifyEmail').onclick = () => document.body.classList.add('by-email');
  }, 100);
})"""


def test_an_email_step_in_phone_mode_is_switched_to_the_email_and_signed_in_to():
    from apply import oracle, submit_guard

    with submit_guard.guarding_on_open(), FakeOracleServer(MACYS_FORM, verify=None) as server, server.open(MACYS_URL) as page:
        page.add_init_script(PHONE_MODE)
        page.reload()
        oracle.sign_in(page, _Accounts(), "Person", agree_to_terms=True)
        assert page.url.endswith("/__fake__/form")
    [email_step] = server.emails
    assert email_step["email"] == "test.person@example.com"


def test_an_apply_that_goes_on_to_the_form_of_an_earlier_sign_in_needs_no_email_step(monkeypatch):
    """Emerson's refill (live 2026-11-27): the browser still held the first attempt's sign-in."""
    from playwright.sync_api import sync_playwright

    from apply import oracle

    monkeypatch.setattr(oracle, "TIMEOUT", 3.0)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        _posting_whose_apply_goes_to(page, "/apply/section/1")
        oracle.sign_in(page, None, "Doe", True)
        assert page.url.endswith("/apply/section/1")
        browser.close()


def test_an_apply_that_shows_no_email_step_is_a_handoff_that_says_what_it_shows(monkeypatch):
    from playwright.sync_api import sync_playwright

    from apply import oracle

    monkeypatch.setattr(oracle, "TIMEOUT", 2.0)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        _posting_whose_apply_goes_to(page, "/apply/draft")
        with pytest.raises(Handoff, match=r'no email step \(.*/apply/draft, "Continue your application"\)'):
            oracle.sign_in(page, None, "Doe", True)
        browser.close()


def test_a_form_lisul_signed_in_to_himself_is_not_signed_in_to_again():
    """On a pause he signed in himself; Resume finds the form's own email field, which can't be edited (KAN-636)."""
    from playwright.sync_api import sync_playwright

    from apply import oracle

    class NoAccounts:
        @property
        def login(self):
            raise AssertionError("no sign-in on a form already open")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content('<label>Email <input type="email" value="lisul@example.com" readonly></label>'
                         '<button>Next</button>')
        oracle.sign_in(page, NoAccounts(), "Elvitigala", agree_to_terms=True)
        browser.close()


def test_resume_on_a_form_section_goes_on_at_once():
    """JPMorgan (live): Resume on section 4 waited 30 s for an email box or an Apply button, then failed (KAN-680)."""
    from playwright.sync_api import sync_playwright

    from apply import oracle

    class NoAccounts:
        @property
        def login(self):
            raise AssertionError("no sign-in on a form already open")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/*", lambda route: route.fulfill(content_type="text/html", body="<h1>More About You</h1><button>Next</button>"))
        page.goto("https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/1/apply/section/4")
        began = time.monotonic()
        oracle.sign_in(page, NoAccounts(), "Elvitigala", agree_to_terms=True)
        assert time.monotonic() - began < 5
        browser.close()


def test_oracles_code_is_searched_by_its_senders_not_by_any_code_subject():
    # JPMorgan (live): the code came from workflow.mail.us2.cloud.oracle.com, and an Amazon code
    # mailed meanwhile matched the old subject-only search.
    from apply.oracle import MAIL_SEARCH
    assert "from:(oracle.com OR oraclecloud.com)" in MAIL_SEARCH
    assert 'subject:"confirm your identity"' in MAIL_SEARCH and "subject:(code" not in MAIL_SEARCH


def test_an_error_gone_as_the_page_goes_on_reads_as_none_at_once():
    """The fake's email step, now and then: an alert counted just before the page went on was gone when read, and the
    read waited Playwright's 30 s for it, so sign-in timed out on a page that had gone on."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    from apply import oracle

    class Gone:
        @property
        def first(self):
            return self

        def count(self):
            return 1

        def inner_text(self, timeout=None):
            assert timeout is not None and timeout <= 1000
            raise PlaywrightTimeout("gone")

    class Page:
        def locator(self, selector):
            return Gone()

    assert oracle._error(Page()) == ""


class _Clock:
    def now(self):
        return NOW


class _Accounts:
    login = "test.person@example.com"
    clock = _Clock()


def test_a_rehearsals_guard_lets_the_email_steps_next_go_on():
    """Honeywell's Oracle site (live): under a rehearsal's guard Next on the email step was blocked as a form's submit
    (KAN-868), since that form holds Oracle's honeypot box beside the email and the page a shut AI Assist pop-up's empty
    text box, and sign-in timed out. Apply's own press of it is a sign-in's, and neither of those is an answer."""
    from apply import oracle, submit_guard

    with submit_guard.guarding_on_open(), FakeOracleServer(MACYS_FORM, verify=None) as server, server.open(MACYS_URL) as page:
        oracle.sign_in(page, _Accounts(), "Person", agree_to_terms=True)
        assert page.url.endswith("/__fake__/form")
    [email_step] = server.emails
    assert (email_step["email"], email_step["accepted"], email_step["honeypot"]) == ("test.person@example.com", True, "")


# OneTrust's preference center as it stays in Emerson's page, shut, once its banner is closed (live 2026-11-27).
SHUT_ONETRUST = """document.addEventListener('DOMContentLoaded', () => document.body.insertAdjacentHTML('beforeend',
  '<div id="onetrust-consent-sdk"><div id="onetrust-pc-sdk" style="display:none">'
  + '<input type="checkbox" id="ot-group-id-C0003" role="switch" checked>'
  + '<input id="vendor-search-handler" type="text" value=""><input id="chkbox-id" type="checkbox"></div></div>'))"""


def test_the_email_steps_next_goes_on_beside_a_shut_cookie_preference_center():
    """Emerson's Oracle site (live): once OneTrust's banner was closed, its shut preference center's ticks and empty
    search box were taken for answers outside the email step's form, so the guard blocked Next as an application's."""
    from apply import oracle, submit_guard

    with submit_guard.guarding_on_open(), FakeOracleServer(MACYS_FORM, verify=None) as server, server.open(MACYS_URL) as page:
        page.add_init_script(SHUT_ONETRUST)
        page.reload()
        assert page.locator("#ot-group-id-C0003").count() == 1
        oracle.sign_in(page, _Accounts(), "Person", agree_to_terms=True)
        assert page.url.endswith("/__fake__/form")
    [email_step] = server.emails
    assert email_step["email"] == "test.person@example.com"


def test_a_next_that_doesnt_go_on_is_a_handoff_not_a_timeout(monkeypatch):
    """A Next the page or a guard stops leaves the email step showing with no error: Lisul goes on himself."""
    from playwright.sync_api import sync_playwright

    from apply import oracle

    monkeypatch.setattr(oracle, "TIMEOUT", 1.0)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content('<form onsubmit="return false"><input type="email"><button>Next</button></form>')
        try:
            oracle.sign_in(page, _Accounts(), "Person", agree_to_terms=True)
        except Handoff as handoff:
            assert "didn't go on past its email step" in str(handoff) and "finish signing in yourself" in str(handoff)
        else:
            raise AssertionError("no Handoff")
        browser.close()
