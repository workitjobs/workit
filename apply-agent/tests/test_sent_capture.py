"""What a held form shows on each press (apply.sent_capture, W11): the values WorkIt keeps as what the application
sent, the student's edits on the form included. Chromium: run by hand with the Filler tests (CI runs no such file)."""

import pytest
from playwright.sync_api import sync_playwright

from apply.model import Question
from apply.sent_capture import Capture

STEP_ONE = """<form onsubmit="return false">
<label for="first_name">First Name</label><input id="first_name" value="Sam">
<label for="year">Graduation Year</label>
<select id="year"><option value="">Pick one</option><option>2027</option><option>2028</option></select>
<div class="field"><label id="school-label">School</label>
  <div class="select__control"><div class="select__singleValue" id="pill">Stony Brook University</div>
  <input role="combobox" aria-labelledby="school-label"></div></div>
<label for="why">Why Acme?</label><textarea id="why">I rode their trains.</textarea>
<label for="pw">Password</label><input id="pw" type="password" value="hunter2">
<button type="button" id="next">Next</button></form>"""
STEP_TWO = """<label for="email">Email</label><input id="email">
<button type="button" id="submit">Submit application</button>"""
QUESTIONS = [Question("first_name", "First Name", "text"), Question("year", "Graduation Year", "select"),
             Question("school", "School", "select"), Question("why", "Why Acme?", "textarea"),
             Question("email", "Email", "text")]


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            yield browser.new_page()
        finally:
            browser.close()


def test_each_press_keeps_what_its_page_shows_and_every_step_stays(page):
    """Fault: an edit typed on the held form, a custom list's new pick or an earlier step's answer was missing from what
    the form sent, or the listener stopped or changed the press."""
    captured = Capture()
    page.set_content(STEP_ONE)
    captured.watch(page, QUESTIONS)
    page.fill("#first_name", "Samuel")
    page.select_option("#year", "2028")
    page.evaluate("document.getElementById('pill').textContent = 'Mansfield University'")  # the list's own pick
    page.fill("#why", "I rode their trains every day.")
    page.evaluate("document.getElementById('next').addEventListener('click', () => window.pressed = true)")
    page.click("#next")
    page.wait_for_function("window.pressed === true")  # the page's own handler still ran

    page.set_content(STEP_TWO)  # the next step is a new document: the next turn puts a listener in it
    captured.watch(page, QUESTIONS)
    page.fill("#email", "sam@example.com")
    page.click("#submit")
    page.wait_for_timeout(200)  # the binding's call lands after the click

    assert captured.values == {"first_name": "Samuel", "year": "2028", "school": "Mansfield University",
                               "why": "I rode their trains every day.", "email": "sam@example.com"}


def test_approve_and_submit_reads_the_form_as_it_is_before_apply_presses(page):
    """Fault: Apply's own press sent a form whose last edit (made with no press since) the record missed."""
    captured = Capture()
    page.set_content(STEP_ONE)
    captured.watch(page, QUESTIONS)
    page.fill("#first_name", "Samuel")

    captured.read_now(page)

    assert captured.values["first_name"] == "Samuel" and "email" not in captured.values
