"""Apply's own plain code on Oracle Recruiting Cloud's application form, which Claude fill fills (Oracle has no
Filler): its dropdowns picked before Claude drives, on one step of Honeywell Aerospace's form as it showed live
(tests/fixtures/oracle/honeywell-step.html)."""

import pytest
from conftest import FIXTURES
from playwright.sync_api import sync_playwright

from apply import claude_fill
from apply.model import Question

STEP = FIXTURES / "oracle" / "honeywell-step.html"


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(STEP.as_uri())
        yield page
        browser.close()


def test_oracles_dropdowns_named_only_by_their_label_are_read_and_picked_country_first(page):
    # Live: no Oracle dropdown names its box but by <label for>, so plain code found none, read no choices and picked
    # nothing, and Claude left the required Country empty. The Address block shows its other fields only once a
    # country is picked; the read names Country under the block's heading.
    questions = [Question("q8", "Address: Country", "select", True),
                 Question("q31", "What is your anticipated graduation year?", "select", True)]

    found = claude_fill._with_options(page, questions)
    picked = claude_fill._pick_in_comboboxes(page, found, {"q8": "United States", "q31": "2027"})

    assert found[0].options[-1] == "United States" and found[1].options == ("2026", "2027", "2028", "2029", "2030")
    assert picked == {"q8": "United States", "q31": "2027"}
    assert page.input_value("#country-29") == "United States"
    assert page.get_by_label("Address Line 1").is_visible()  # the block's next fields, now shown in order


def test_a_choice_under_the_error_paragraph_that_covers_the_open_list_is_still_picked(page):
    # Live: "This info is required." lay over the graduation month's open list and took every click on December;
    # the read listed no choices, so the plan gave "December 2027", which no option is.
    month = Question("q32", "What is your anticipated graduation month?", "select", True)

    [found] = claude_fill._with_options(page, [month])
    picked = claude_fill._pick_in_comboboxes(page, [found], {"q32": "December"})

    assert found.options[0] == "January" and found.options[-1] == "December"
    assert picked == {"q32": "December"}
    assert page.input_value("[id=\"300000007362128-25\"]") == "December"
