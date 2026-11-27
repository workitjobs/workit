"""Apply's own plain code on Oracle Recruiting Cloud's application form, which Claude fill fills (Oracle has no
Filler): its dropdowns picked before Claude drives, on one step of Honeywell Aerospace's form as it showed live
(tests/fixtures/oracle/honeywell-step.html)."""

from datetime import date

import pytest
from conftest import APPLY, FIXTURES
from playwright.sync_api import sync_playwright

from apply import claude_fill, fill_engine, send_button
from apply.model import Posting, Question
from apply.profile import ApplicantProfile

STEP = FIXTURES / "oracle" / "honeywell-step.html"
LAST_STEP = FIXTURES / "oracle" / "bgc-last-step.html"
PROFILE = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
POSTING = Posting("p", "Honeywell Aerospace", "Embedded Engineering Intern",
                  "https://icfcjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/Aerospace/job/120770")


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


def test_the_phone_country_code_is_picked_by_plain_code_though_its_box_shows_only_the_code(page):
    # BGC's form (live 2026-11-27): plain code picked "+1 (United States)", but the box shows "+1", so the pick
    # read as failed. Each fill round left it to Claude, which spent turns on the open list, and the read-back "+1"
    # sent it to be planned again.
    code = Question("q7", "Country code", "select", True)

    [found] = claude_fill._with_options(page, [code])
    picked = claude_fill._pick_in_comboboxes(page, [found], {"q7": "+1 (United States)"})

    assert "+1 (United States)" in found.options
    assert picked == {"q7": "+1 (United States)"}
    assert page.input_value("#country-codes-dropdownphoneNumber") == "+1"


def test_a_box_that_shows_another_choices_code_is_not_read_as_the_choice(page):
    code = Question("q7", "Country code", "select", True)
    [found] = claude_fill._with_options(page, [code])

    assert claude_fill._pick_in_comboboxes(page, [found], {"q7": "+44 (United Kingdom)"}) == {"q7": "+44 (United Kingdom)"}
    box = page.locator("#country-codes-dropdownphoneNumber")
    assert not claude_fill._shows_choice(box, "+1 (United States)")
    assert not claude_fill._shows_choice(box, "+4")


def test_each_part_of_the_address_block_is_planned_from_its_own_fact_not_the_street():
    # Live: the read named the block's fields under its heading, and the plan put the street in "Address: Country".
    questions = [Question("q8", "Address: Country", "select", True, ("Canada", "United States")),
                 Question("q9", "Address: Address Line 1", "text", True),
                 Question("q10", "Address: City", "text", True)]

    plan = fill_engine.plan(questions, POSTING, PROFILE, today=date(2026, 11, 25))

    assert {name: plan.answers.get(name) for name in ("q8", "q9", "q10")} == \
        {"q8": "United States", "q9": "1 Main St", "q10": "Springfield"}


def test_the_ethnicity_box_and_the_race_list_get_their_own_choices_and_the_races_are_ticked(page, tmp_path):
    # Live: the read gave Ethnicity, a group of one box ("I am Hispanic or Latino."), no choices, so the plan put the
    # race in it; and the race list was left to Claude.
    questions = [Question("q11", "Ethnicity (I am Hispanic or Latino.)", "select", False),
                 Question("q12", "Select the races you identify with.", "multi_select", False)]

    found = claude_fill._with_options(page, questions)
    facts = (FIXTURES / "planner-profile.yaml").read_text().replace("hispanic_or_latino: decline", "hispanic_or_latino: false")
    (tmp_path / "profile.yaml").write_text(facts.replace("race: decline", "race: Asian"))
    profile = ApplicantProfile.load(tmp_path / "profile.yaml", APPLY / "policies.default.yaml")
    plan = fill_engine.plan(found, POSTING, profile, today=date(2026, 11, 25))
    ticked = claude_fill._tick_in_groups(page, found, {"q12": ["Asian"]})

    assert found[0].options == ("I am Hispanic or Latino.",)
    assert found[1].options == ("American Indian or Alaska Native", "Asian", "Black or African American", "White",
                                "Two or More Races")
    assert "q11" not in plan.answers  # not Hispanic: its one box stays unticked
    assert ticked == {"q12": ["Asian"]}
    assert page.is_checked("#dq-option-5") and not page.is_checked("#dq-option-4")


@pytest.mark.parametrize(("level", "signed"), [("careful", False), ("balanced", False), ("full_auto", True)])
def test_oracles_e_signature_is_signed_only_at_full_auto(tmp_path, level, signed):
    # BGC's Oracle form (live 2026-11-27): at full_auto its "E-Signature: Full Name" held the form for Lisul to sign.
    (tmp_path / "profile.yaml").write_text((FIXTURES / "planner-profile.yaml").read_text())
    (tmp_path / "policies.yaml").write_text(f"safety_level: {level}\n")
    profile = ApplicantProfile.load(tmp_path / "profile.yaml", APPLY / "policies.default.yaml")
    question = Question("q25", "E-Signature: Full Name", "text", True)

    plan = fill_engine.plan([question], POSTING, profile, today=date(2026, 11, 27))

    first, last = profile.get("identity.legal_first_name"), profile.get("identity.legal_last_name")
    assert plan.answers.get("q25") == (f"{first} {last}" if signed else None)
    assert plan.attestations == ({} if signed else {"q25": "E-Signature: Full Name"})


@pytest.fixture
def last_step():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(LAST_STEP.as_uri())
        yield page
        browser.close()


def test_oracles_own_submit_on_the_last_step_is_read_by_plain_code(last_step):
    # BGC's form (live 2026-11-27): 33 of 33 fields filled, then Haiku named no button that sends beside Oracle's
    # Submit, whose words come from i18n, and the fill was a Handoff instead of held at its last step.
    assert claude_fill._last_step_submit(last_step) == "Submit"
    assert last_step.evaluate(send_button.FIND) == ["Submit"]  # the one button Approve and submit presses


def test_a_step_without_oracles_submit_names_none(page):
    assert claude_fill._last_step_submit(page) == ""


@pytest.mark.parametrize("change", [
    "b => b.disabled = true",  # a required answer missing: Oracle keeps it disabled (isSubmitEnabled)
    "b => b.hidden = true",
    "b => b.querySelector('span').textContent = 'Save'",  # words that send nothing
    "b => b.after(b.cloneNode(true))",  # two of them: never a guess between them
])
def test_oracles_submit_is_named_only_when_one_shows_enabled_and_its_words_send(last_step, change):
    last_step.locator(claude_fill.LAST_STEP_SUBMIT).evaluate(change)

    assert claude_fill._last_step_submit(last_step) == ""
