"""Apply signs in from the vault at a sign-in pause (apply.vault_sign_in, rehearsal._from_vault), on a stand-in page
and a MemoryStore: no browser, no keychain."""

import json

import pytest

from apply import captcha, rehearsal, submit_guard, vault_sign_in
from apply.vault import Login, MemoryStore
from apply.vault_sign_in import FAILED, LEFT, SIGNED_IN

SECRET = "Hunter2!Secret"
EMAIL = "me@example.com"


class Box:
    def __init__(self, page, kind):
        self.page, self.kind, self.value = page, kind, ""

    def is_visible(self):
        return self in self.page.boxes

    def fill(self, value, **options):
        self.value = value

    def input_value(self):
        return self.value

    def press(self, key):
        assert key == "Enter"
        assert self.page.let, "pressed with the guards' sign-in allowance off"
        self.page.enter(self)


class Locator:
    def __init__(self, found):
        self._found = found

    def all(self):
        return list(self._found)


class Page:
    """A sign-in page. `steps`: "one" (email and password together) or "two" (email first). The right password
    goes past it; a wrong one leaves it showing, as a site's refusal does."""

    def __init__(self, url, steps="one", password=SECRET, then="https://amazon.jobs/en/apply", boxes=None):
        self.url, self.password, self.then, self.let = url, password, then, False
        self.lets, self.sent = [], []
        email = Box(self, "email")
        self.boxes = boxes(self) if boxes else [email] if steps == "two" else [email, Box(self, "password")]

    def locator(self, selector):
        if selector == vault_sign_in._SIGN_UP:
            return Locator([])
        kind = "password" if selector == vault_sign_in._PASSWORD else "email"
        return Locator([b for b in self.boxes if b.kind == kind])

    def wait_for_timeout(self, ms):
        pass

    def enter(self, box):
        self.sent.append((box.kind, box.value))
        if box.kind == "email":
            self.boxes = [box, Box(self, "password")]
        elif box.value == self.password:
            self.boxes, self.url = [], self.then


def let(page, on):
    page.let = on
    page.lets.append(on)


@pytest.fixture(autouse=True)
def no_captcha(monkeypatch):
    monkeypatch.setattr(captcha, "pending", lambda page: False)
    vault_sign_in.forget_run()
    yield
    vault_sign_in.forget_run()


def store():
    return MemoryStore(Login("amazon.jobs", EMAIL, SECRET))


def go(page, tried=None, store=store):
    return vault_sign_in.sign_in(page, set() if tried is None else tried, store(), let, settle_s=0)


@pytest.fixture(autouse=True)
def no_settle(monkeypatch):
    monkeypatch.setattr(vault_sign_in, "SETTLED_S", 0)


def test_it_signs_in_on_the_exact_https_host():
    page = Page("https://amazon.jobs/en/login")
    done = go(page)
    assert done.how == SIGNED_IN
    assert page.sent == [("password", SECRET)]
    assert page.lets == [True, False]  # the guards' allowance only for its own press
    assert SECRET not in done.why


def test_it_signs_in_an_email_first_step():
    page = Page("https://amazon.jobs/en/login", steps="two")
    assert go(page).how == SIGNED_IN
    assert page.sent == [("email", EMAIL), ("password", SECRET)]


@pytest.mark.parametrize("url", ["http://amazon.jobs/en/login", "https://amazon.jobs.evil.com/login",
                                 "https://amazon.jobs@evil.com/login", "https://www.amazon.jobs/login"])
def test_a_lookalike_or_http_page_gets_nothing(url):
    page = Page(url)
    assert go(page).how == LEFT
    assert page.sent == [] and all(box.value == "" for box in page.boxes)


def test_a_page_that_moves_off_the_host_after_the_email_gets_no_password():
    page = Page("https://amazon.jobs/en/login", steps="two")
    real = page.enter

    def to_elsewhere(box):
        real(box)
        page.url = "https://amazon.jobs.evil.com/password"
    page.enter = to_elsewhere
    assert go(page).how == LEFT
    assert all(box.value != SECRET for box in page.boxes)


def test_a_wrong_password_pauses_once_and_is_never_tried_again():
    page = Page("https://amazon.jobs/en/login", password="Another1!")
    done = go(page)
    assert done.how == FAILED and done.why.startswith("Sign-in failed at amazon.jobs")
    assert [box.value for box in page.boxes if box.kind == "password"] == [""]  # emptied after the press
    again = Page("https://amazon.jobs/en/login", password="Another1!")
    assert go(again).how == FAILED
    assert again.sent == []  # another tile's page: nothing typed


def test_a_password_box_back_on_a_tried_host_is_a_refused_password():
    """The page went past the password, and the fill's next sign-in pause there asks for it again."""
    tried = set()
    assert go(Page("https://amazon.jobs/en/login"), tried).how == SIGNED_IN
    page = Page("https://amazon.jobs/en/login")
    assert go(page, tried).how == FAILED and page.sent == []
    assert go(Page("https://amazon.jobs/en/login")).how == FAILED  # nor in any other tile


def test_a_password_saved_anew_is_tried_again():
    go(Page("https://amazon.jobs/en/login", password="Another1!"))
    fixed = lambda: MemoryStore(Login("amazon.jobs", EMAIL, "Another1!"))
    assert go(Page("https://amazon.jobs/en/login", password="Another1!"), store=fixed).how == SIGNED_IN


def test_a_page_that_reloads_with_its_password_box_is_refused(monkeypatch):
    """A refusal that reloads the page: the box is gone for a moment, then back."""
    monkeypatch.setattr(vault_sign_in, "SETTLED_S", 0.05)
    page = Page("https://amazon.jobs/en/login", password="Another1!")
    looks = [0]
    real = page.locator

    def blinks(selector):
        looks[0] += 1
        if selector == vault_sign_in._PASSWORD and page.sent and looks[0] % 7 == 0:
            return Locator([])
        return real(selector)
    page.locator = blinks
    assert go(page).how == FAILED


def test_a_captcha_after_the_press_is_the_students(monkeypatch):
    page = Page("https://amazon.jobs/en/login")
    monkeypatch.setattr(captcha, "pending", lambda p: bool(p.sent))
    assert go(page).how == LEFT


def test_a_new_accounts_form_is_left_alone():
    class Named(Box):
        def is_visible(self):
            return True
    page = Page("https://amazon.jobs/en/login")
    real = page.locator
    page.locator = lambda selector: Locator([Named(page, "name")]) if selector == vault_sign_in._SIGN_UP \
        else real(selector)
    page.boxes.append(Box(page, "name"))
    assert go(page).how == LEFT and page.sent == []


def test_a_captcha_is_the_students(monkeypatch):
    monkeypatch.setattr(captcha, "pending", lambda page: True)
    page = Page("https://amazon.jobs/en/login")
    assert go(page).how == LEFT and page.sent == []


def test_two_password_boxes_are_a_sign_up_and_left_alone():
    page = Page("https://amazon.jobs/en/login",
                boxes=lambda p: [Box(p, "email"), Box(p, "password"), Box(p, "password")])
    assert go(page).how == LEFT and page.sent == []


def test_a_code_step_after_the_password_is_the_students():
    """2FA: the password goes in, then a code box shows. The vault types nothing more, and the next pause is his."""
    page = Page("https://amazon.jobs/en/login")
    real = page.enter

    def to_code(box):
        real(box)
        page.boxes, page.url = [Box(page, "code")], "https://amazon.jobs/en/verify"
    page.enter = to_code
    tried = set()
    assert go(page, tried).how == SIGNED_IN  # past the password: the fill's own check sees the code step
    assert go(page, tried).how == LEFT  # the code step: no password box, nothing typed, the student's


class Site:
    def __init__(self, page):
        self._page = page

    def held_page(self):
        return self._page


def summary():
    return rehearsal.Rehearsed(rehearsal.Posting("1", "Amazon", "Intern", "https://amazon.jobs/en/jobs/1"),
                               rehearsal.SIGN_IN, "Sign in to amazon.jobs")


@pytest.mark.parametrize("password", [SECRET, "Another1!"])
def test_no_password_reaches_the_pause_the_tile_or_a_log(password, monkeypatch, capsys):
    monkeypatch.setattr(vault_sign_in.vault, "STORE", store())
    monkeypatch.setattr(vault_sign_in, "SETTLE_S", 0)
    monkeypatch.setattr(vault_sign_in, "SETTLED_S", 0)
    monkeypatch.setattr(submit_guard, "let_account_click", let)  # the guards' own allowance, on the stand-in page
    stopped = summary()
    went = rehearsal._from_vault(stopped, Site(Page("https://amazon.jobs/en/login", password=password)), set())
    assert went == (rehearsal.VAULT if password == SECRET else False)
    out = capsys.readouterr()
    shown = json.dumps(stopped.__dict__, default=str) + stopped.line() + out.out + out.err
    assert SECRET not in shown
    if password != SECRET:
        assert stopped.why.startswith("Sign-in failed at amazon.jobs")


def test_a_keychain_that_refuses_is_said_in_the_pause(monkeypatch, capsys):
    class Locked:
        def get(self, host):
            raise RuntimeError("the keychain would not give the vault's item for amazon.jobs: locked")
    monkeypatch.setattr(vault_sign_in.vault, "STORE", Locked())
    stopped = summary()
    assert rehearsal._from_vault(stopped, Site(Page("https://amazon.jobs/en/login")), set()) is False
    assert "couldn't read Keychain" in stopped.why and "couldn't read Keychain" in capsys.readouterr().err


def test_a_page_handed_to_the_student_is_not_signed_in():
    stopped = summary()
    assert rehearsal._from_vault(stopped, Site(None), set()) is False
    assert stopped.why == "Sign in to amazon.jobs"


def test_a_held_page_is_none_once_lifted_or_closed():
    kept = rehearsal._Kept(object(), 0)
    assert kept.held_page() is None

    class Open:
        def is_closed(self):
            return False
    kept._page = Open()
    assert kept.held_page() is kept._page
    kept._lifted = True
    assert kept.held_page() is None


def test_a_page_whose_chrome_has_a_devtools_port_gets_nothing():
    """A CDP Worker's page (a Playwright page: it has a context) listens on a TCP DevTools port."""
    page = Page("https://amazon.jobs/en/login")
    page.context = object()
    done = go(page)
    assert done.how == LEFT and done.said and "DevTools port" in done.why
    assert page.sent == [] and all(box.value == "" for box in page.boxes)


def test_a_plain_workers_page_has_no_devtools_port():
    from apply.plain.page import PortPage

    assert vault_sign_in.debug_port(PortPage.__new__(PortPage)) is False


def test_the_open_port_is_said_in_the_pause(monkeypatch):
    monkeypatch.setattr(vault_sign_in.vault, "STORE", store())
    page = Page("https://amazon.jobs/en/login")
    page.context = object()
    stopped = summary()
    assert rehearsal._from_vault(stopped, Site(page), set()) is False
    assert "DevTools port" in stopped.why
