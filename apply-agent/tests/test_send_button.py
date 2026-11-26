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
