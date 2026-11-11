"""The amazon.jobs Filler (KAN-765) on the Fill engine's fake Amazon form (its test/fake-amazon-page.js): plain code,
no Claude. It visits every step, the ones an old Amazon profile ticked too, presses each step's own Continue, reads
back what Amazon kept, stops for Lisul on the Acknowledgement, and never presses Submit application. The live form is
proved by rehearsing an Amazon posting (apply rehearse <link>)."""

import json
from contextlib import contextmanager

import pytest
from playwright.sync_api import sync_playwright

from apply.amazon import AmazonFiller
from apply.fill_engine import ENGINE_DIR, attestations
from apply.model import Handoff, MoreQuestions, Posting

FORM = "https://www.amazon.jobs/en-US/applicant/jobs/1234567/apply"
SCRIPT = ENGINE_DIR / "test" / "fake-amazon-page.js"
YES_NO = ["Yes", "No"]
ACK = "By checking this box, I confirm that I have read and agree to the above acknowledgements."
# A small Amazon form, as the engine's fake draws it: two ticked steps an old profile filled, then the step Amazon opens.
STEPS = [
    {"id": "GENERAL", "title": "General questions", "completed": True, "fields": [
        {"key": "RELOCATE", "label": "Are you willing to relocate?", "kind": "select", "options": YES_NO, "old": "No"}]},
    {"id": "EDUCATION", "title": "Education", "completed": True, "fields": [
        {"key": "MINOR", "label": "Minor", "kind": "select", "options": ["None", "Applied Mathematics"], "old": "Applied Mathematics"},
        {"key": "GRAD", "label": "Expected graduation date", "kind": "date", "format": "YYYY-MM-DD", "required": True, "old": "2027-05-31"}]},
    {"id": "JOB", "title": "Job-specific questions", "fields": [
        {"key": "AGE", "label": "Are you 18 years of age or older?", "kind": "select", "required": True, "options": YES_NO},
        {"key": "CPP", "label": "Describe your experience coding in C or C++.", "kind": "text", "required": True}]},
    {"id": "ACKNOWLEDGEMENT", "title": "Acknowledgement", "completed": True,
     "intro": "All information provided in my application is truthful and accurate.",
     "fields": [{"key": "ACK", "label": ACK, "kind": "checkbox", "required": True, "old": "Yes"}]},
]
ANSWERS = {"Are you willing to relocate?": "Yes", "Minor": "None", "Expected graduation date (YYYY-MM-DD)": "2028-05-21",
           "Are you 18 years of age or older?": "Yes", "Describe your experience coding in C or C++.": "C++ firmware for a robot."}


class Site:
    """The one page an Application's Filler keeps open (OnePage)."""

    def __init__(self, page):
        self.page = page

    @contextmanager
    def open(self, url):
        yield self.page


@contextmanager
def amazon(steps=STEPS, **setup):
    if not SCRIPT.exists():
        pytest.skip("the engine checkout has no fake Amazon form (git submodule update --init)")
    sent: list[str] = []
    body = (f"<!doctype html><html><head><title>Apply to a Job | Amazon.jobs</title></head><body><script>"
            f"window.__fakeAmazon = {json.dumps({'steps': steps, **setup})};</script>"
            f"<script>{SCRIPT.read_text()}</script></body></html>")

    def handle(route):
        if route.request.method != "GET":
            sent.append(route.request.url)
        route.fulfill(body=body, content_type="text/html")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context()
            context.route(lambda url: True, handle)  # no real site is ever reached
            page = context.new_page()
            page.goto(FORM)
            yield page, sent
        finally:
            browser.close()


def run(filler, page, stop_at_handoff=True):
    """Fill as the Worker does: plan each step's new questions (here: by label) and fill again."""
    questions = filler.question_set(FORM, Site(page))
    answers = {}
    for _ in range(10):
        answers |= {q.name: ANSWERS[q.label] for q in questions if q.label in ANSWERS}
        try:
            return questions, filler.fill(page, questions, answers)
        except MoreQuestions as more:
            questions += more.questions
    raise AssertionError("the fill never ended")


def test_an_amazon_jobs_link_is_amazons_filler():
    assert Posting("1", "", "", "https://www.amazon.jobs/en/jobs/10587087/system-development-engineer").job_system == "amazon"
    assert Posting("1", "", "", "https://account.amazon.jobs/en-US/applicant/jobs/10587087/apply").job_system == "amazon"
    assert AmazonFiller(None).form_url("https://www.amazon.jobs/en/jobs/10587087/x") == FORM.replace("1234567", "10587087")


def test_every_step_is_filled_the_ticked_ones_too_and_the_acknowledgement_stops_for_lisul():
    with amazon() as (page, sent):
        filler = AmazonFiller(None)
        with pytest.raises(Handoff, match="yourself on this page"):
            run(filler, page)
        saved = page.evaluate("window.__fakeAmazonSaved")
        assert saved["RELOCATE"] == "Yes" and saved["MINOR"] == "None" and saved["GRAD"] == "2028-05-21"
        assert saved["AGE"] == "Yes"
        # Read back after Continue: what Amazon kept, by the names the open cards gave.
        assert filler.shown_so_far["Education / Minor"] == "None"
        assert filler.shown_so_far["Education / Expected graduation date (YYYY-MM-DD)"] == "2028-05-21"
        assert filler.step == "Acknowledgement"
        assert page.evaluate("window.__fakeAmazonSubmitted") is False
        assert sent == []


def test_after_lisul_ticks_the_acknowledgement_and_resumes_the_fill_stops_on_review_and_submit_unsent():
    # Unticked at first: a box the page showed ticked at the pause and still shows ticked is not his (KAN-676).
    unticked = [*STEPS[:3], {**STEPS[3], "fields": [{**STEPS[3]["fields"][0], "old": None}]}]
    with amazon(unticked) as (page, sent):
        filler = AmazonFiller(None)
        questions = None
        try:
            run(filler, page)
        except Handoff:
            questions = filler._known
        page.check("#ACK-box", force=True)  # Lisul's own tick, before he presses Resume
        filler.resumed(page)
        answers = {q.name: ANSWERS[q.label] for q in questions if q.label in ANSWERS}
        readback = filler.fill(page, questions, answers)
        assert readback["Job-specific questions / Are you 18 years of age or older?"] == "Yes"
        assert page.evaluate("window.__fakeAmazonContinues")[-1] == "Acknowledgement"
        assert page.evaluate("window.__fakeAmazonSubmitted") is False
        assert sent == []
        with pytest.raises(Handoff, match="Submit application is yours"):
            filler.submit(page)


def test_the_acknowledgement_is_an_attestation_the_plan_leaves_to_lisul():
    with amazon() as (page, _):
        filler = AmazonFiller(None)
        try:
            run(filler, page)
        except Handoff:
            pass
        ack = [q for q in filler._known if q.label == ACK]
        assert ack and {ack[0].name} == attestations(ack)


def test_amazons_sign_in_is_lisuls():
    with amazon() as (page, _):
        page.set_content("<form name=signIn><input type=email name=email id=ap_email><input type=password></form>")
        with pytest.raises(Handoff, match="Sign in to amazon.jobs"):
            AmazonFiller(None).question_set(FORM, Site(page))
        assert page.input_value("#ap_email") == ""
