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
ADDRESS = FIXTURES / "oracle" / "honeywell-address.html"
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


@pytest.fixture
def address():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(ADDRESS.as_uri())
        yield page
        browser.close()


ADDRESS_QUESTIONS = [Question("q39", "City", "select", True), Question("q40", "State", "select", True),
                     Question("q41", "County", "select", True), Question("q42", "Zip Code", "select", True)]


def test_oracles_city_county_and_zip_are_searched_and_picked_by_plain_code(address):
    # Live (Honeywell, 2026-11-27): the read gave City, County and Zip Code no choices, as their lists show none until
    # searched, so plain code skipped them, and Claude spent 21 turns and 5 million tokens on the block. City lists
    # every place of that name; the plan's county and state tell which. County and Zip Code list only the city's.
    answers = {"q39": "Springfield", "q40": "IL", "q41": "Sangamon", "q42": "62701"}

    picked = claude_fill._pick_in_comboboxes(address, ADDRESS_QUESTIONS, answers)

    assert picked == answers
    assert address.evaluate("document.body.dataset.city") == "Springfield, Sangamon, IL"
    assert [address.input_value(f"#{box}") for box in ("city-57", "region2-58", "region1-59", "postalCode-60")] == \
        ["Springfield", "IL", "Sangamon", "62701"]


def test_a_searched_place_the_list_names_twice_or_never_is_left_to_claude_and_its_words_cleared(address):
    # No county or state in the plan to tell the three Springfields apart, and a city the list has no place for.
    picked = claude_fill._pick_in_comboboxes(address, ADDRESS_QUESTIONS[:1], {"q39": "Springfield"})
    assert picked == {} and address.input_value("#city-57") == ""

    picked = claude_fill._pick_in_comboboxes(address, ADDRESS_QUESTIONS[:1], {"q39": "Gotham", "q40": "IL"})
    assert picked == {} and address.input_value("#city-57") == ""


def test_a_search_list_option_fits_by_its_first_part_then_by_the_parts_the_plan_gives():
    names = ("Springfield, Sangamon, IL", "Springfield, Clark, OH", "Springfield Gardens, Queens, NY")
    assert claude_fill._fitting(names, "Springfield", {"sangamon", "il"}) == ["Springfield, Sangamon, IL"]
    assert claude_fill._fitting(names, "Springfield", {"il"}) == []
    assert claude_fill._fitting(names, "Springfield Gardens", set()) == ["Springfield Gardens, Queens, NY"]
    assert claude_fill._fitting(("62701, Springfield, Sangamon, IL",), "62701", set()) == ["62701, Springfield, Sangamon, IL"]
    assert claude_fill._fitting(names, "Springfield, Clark, OH", {"il"}) == ["Springfield, Clark, OH"]


def test_the_first_places_a_search_list_shows_unsearched_are_never_read_as_its_choices_and_the_plan_fills_it(address):
    # Live (Honeywell, run 24): opened with nothing typed, County listed its first 500 ("Abbeville, SC" on); read as
    # its choices, the plan found the applicant's county among none of them, and City, County and Zip Code went blank.
    # And "Address: County", asked as the home address's, was planned the whole address.
    questions = [Question("q42", "Address: City", "select", True), Question("q43", "Address: State", "select", True),
                 Question("q44", "Address: County", "select", True), Question("q45", "Address: Zip Code", "select", True)]

    profile = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
    profile.set_answered("County", "Sangamon")  # the applicant's county, as Apply keeps it

    found = claude_fill._with_options(address, questions)
    plan = fill_engine.plan(found, POSTING, profile, today=date(2026, 11, 27))
    picked = claude_fill._pick_in_comboboxes(address, found, plan.answers)

    assert [q.options for q in found] == [(), (), (), ()]
    assert {name: plan.answers.get(name) for name in ("q42", "q43", "q44", "q45")} == \
        {"q42": "Springfield", "q43": "IL", "q44": "Sangamon", "q45": "62701"}
    assert picked == {"q42": "Springfield", "q43": "IL", "q44": "Sangamon", "q45": "62701"}
    assert address.evaluate("document.body.dataset.city") == "Springfield, Sangamon, IL"


def test_a_place_answered_as_its_whole_option_is_picked_once_and_never_pressed_again(address):
    # Lisul answered City "<city>, <county>, <state>", the whole option, but the box shows only the city: read as
    # unpicked, Claude opened the list again, where a click on the picked option empties the box.
    city = [Question("q42", "Address: City", "select", True)]
    whole = {"q42": "Springfield, Clark, OH"}

    assert claude_fill._pick_in_comboboxes(address, city, whole) == whole
    assert address.evaluate("document.body.dataset.city") == "Springfield, Clark, OH"
    assert claude_fill._pick_in_comboboxes(address, city, whole) == whole
    assert address.input_value("#city-57") == "Springfield"
