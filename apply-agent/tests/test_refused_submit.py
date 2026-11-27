"""Why a Submit Apply pressed didn't go in, as the form says it (apply.refused_submit): each field error with the
question it is about, so the hold fixes that field and presses once more, or hands the form over in the page's words."""

from playwright.sync_api import sync_playwright

from apply.model import Question
from apply.refused_submit import FieldError, errors, fixable

# Greenhouse's demographic consent as Epic Games' form showed it after Apply's press (live, 2026-11-26): a lone box
# whose own id is `<name>_1`, its message in the block around it; and Apply's own note, which is no error.
CONSENT = """<form>
  <div id="gdpr_demographic_data_consent_given" class="checkbox">
    <input type="checkbox" id="gdpr_demographic_data_consent_given_1" value="1">
    <label for="gdpr_demographic_data_consent_given_1">By checking this box, I consent to Epic Games collecting,
      storing, and processing my responses to the demographic data surveys above.*</label>
    <p class="helper-text helper-text--error">Please accept the terms to proceed.</p>
  </div>
  <div id="apply-note" class="error">Apply's own note</div>
</form>"""

CONSENT_Q = Question("gdpr_demographic_data_consent_given", "By checking this box, I consent to Epic Games ...",
                     "multi_select", True, ["By checking this box, I consent to Epic Games ..."])


def test_a_lone_boxs_error_is_known_by_its_questions_name_and_apply_notes_are_none():
    """Fault: the consent's message is tied to its box's own id (`..._1`) only, so no question matches and Apply hands
    over a form it could fix; or Apply's own red note is read as the job site's error."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort())
        page.set_content(CONSENT)
        found = errors(page)
        browser.close()

    assert [e.words for e in found] == ["Please accept the terms to proceed."]
    assert fixable(found, [CONSENT_Q]) == [CONSENT_Q]


def test_a_message_about_no_question_of_the_form_leaves_nothing_to_fix():
    """Fault: one message Apply can tie to a question is fixed and Submit pressed again, while another (a whole-form
    error) still stands: the second press is refused too, or sends a form the student never saw fixed."""
    tied = FieldError("Please accept the terms to proceed.", ("gdpr_demographic_data_consent_given",))
    whole = FieldError("Something went wrong. Please try again later.")

    assert fixable([tied, whole], [CONSENT_Q]) == []
    assert fixable([], [CONSENT_Q]) == []
