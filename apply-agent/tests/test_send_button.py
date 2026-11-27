"""Approve and submit's press (apply.send_button): only a Submit button Apply is sure of."""

import pytest
from playwright.sync_api import sync_playwright

from apply import send_button


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        launched = playwright.chromium.launch()
        yield launched
        launched.close()


def page_of(browser, html: str):
    page = browser.new_page()
    page.set_content(html + "<script>window.pressed = []; document.addEventListener('click', e => "
                            "window.pressed.push(e.target.innerText || e.target.value));</script>")
    return page


def test_it_presses_the_one_visible_submit_button_even_in_a_frame(browser):
    page = page_of(browser, """<button>Back</button><button hidden>Submit</button><button disabled>Send</button>
        <iframe srcdoc="<form><input type=submit value='Submit application'></form>"></iframe>""")
    page.wait_for_timeout(200)
    assert send_button.press(page) == "Submit application"


def test_none_or_several_and_it_presses_nothing(browser):
    page = page_of(browser, "<button>Next</button><button>Save draft</button>")
    with pytest.raises(send_button.NotPressed, match="no Submit button"):
        send_button.press(page)
    page = page_of(browser, "<button>Submit</button><button>Send to a friend</button>")
    with pytest.raises(send_button.NotPressed, match="'Submit', 'Send to a friend'"):
        send_button.press(page)
    assert page.evaluate("window.pressed") == []


def test_a_code_steps_send_new_code_is_never_the_submit(browser):
    """Fault (Emerson on Oracle, live 2026-11-27): on "You're almost done" (six boxes, VERIFY, Send New Code) the press
    after the code landed on Send New Code, the one button saying "send", which voided the code just typed."""
    page = page_of(browser, "<button>VERIFY</button><button>Send New Code</button><a role=button>Resend code</a>")
    with pytest.raises(send_button.NotPressed, match="no Submit button"):
        send_button.press(page)
    assert page.evaluate("window.pressed") == []


def test_a_press_that_sends_the_page_away_is_unsure_never_none(browser):
    """Fault: a Submit whose page navigates away (Lever's whole-page post) ends the click with an error, and Apply
    reads that as no Submit button found, so it never watches for the job site's confirmation."""
    page = page_of(browser, """<button onclick="setTimeout(() => location.href = 'about:blank#thanks', 0)">Submit</button>""")
    real = page.frames[0].locator

    class Lost:
        def __init__(self, selector):
            self._real = real(selector)

        def click(self, **kwargs):
            self._real.click(**kwargs)
            raise RuntimeError("Navigated: the click's reply was lost")
    page.frames[0].locator = Lost
    with pytest.raises(send_button.Unsure) as unsure:
        send_button.press(page)
    assert unsure.value.words == "Submit"


def test_a_form_with_a_required_field_blank_is_never_pressed_and_the_field_is_named(browser):
    """Fault: Send anyway pressed Submit on a form with a required answer still blank (Veeva, live 2026-11-27), and
    the press was told as maybe sent, though the browser itself sends no form with a required field empty."""
    page = page_of(browser, """<form><ul>
        <li class="application-question"><div class="application-label">Question 2: Tell us about a project ✱</div>
          <textarea name="cards[a][field1]" required></textarea></li>
        <li class="application-question"><label for="n">Full name</label><input id="n" name="name" required value="Ada"></li>
        <li><input type="hidden" name="token" required></li>
        </ul><button type="button">Submit application</button></form>""")
    with pytest.raises(send_button.NotPressed, match="'Question 2: Tell us about a project'") as refused:
        send_button.press(page)
    assert "Full name" not in str(refused.value)
    assert page.evaluate("window.pressed") == []
    page.fill("textarea", "A robot")
    assert send_button.press(page) == "Submit application"


def test_a_required_checkbox_group_with_a_box_ticked_is_answered(browser):
    """Fault: SambaNova's "Preferred office?" (2026-11-27), a Greenhouse group whose every box is `required`, had San
    Jose and Austin ticked, yet each unticked box was told as a required field blank, so Submit was never pressed."""
    boxes = "".join(f'<label><input type="checkbox" required name="question_1[]" value="{v}"{" checked" * ticked}>{v}'
                    "</label>" for v, ticked in (("San Jose, CA", True), ("Austin, TX", True), ("Remote - US", False),
                                                 ("N/A", False)))
    form = ('<form><fieldset class="checkbox"><legend class="label">Preferred office? <span class="required">*</span>'
            f"</legend>{boxes}</fieldset>"'<button type="button">Submit application</button></form>')
    assert send_button.press(page_of(browser, form)) == "Submit application"
    page = page_of(browser, form.replace(" checked", ""))
    assert send_button.blank_required(page) == ["Preferred office?"]


def test_a_click_that_never_reached_submit_is_not_pressed_never_unsure(browser):
    """Fault: a cookie banner over Submit kept the click off it until it timed out, and Apply read that as a press
    whose reply was lost: "it may have gone in", though nothing was sent."""
    page = page_of(browser, """<button style="position:fixed;bottom:10px;left:10px">Submit application</button>
        <div id="cookie-banner" style="position:fixed;inset:auto 0 0 0;height:120px;background:#000"></div>""")
    real = page.frames[0].locator

    class Quick:
        def __init__(self, selector):
            self._real = real(selector)

        def click(self, **kwargs):
            self._real.click(**{**kwargs, "timeout": 500})
    page.frames[0].locator = Quick
    with pytest.raises(send_button.NotPressed, match="cookie-banner"):
        send_button.press(page)
    assert page.evaluate("window.pressed") == []
