"""Entering an emailed code the student gave (apply.code_box.put), on fake code boxes: no browser, in CI."""

import pytest

from apply import code_box

CODE = "OxNbtPnI"  # Greenhouse's: eight case-sensitive letters and digits


class Box:
    """One code box as a React form keeps it: its value is what the last `input` event left (fill sends one), and
    `change` is heard too. `takes` says what a fill leaves (a box that heeds only keys takes nothing from a fill)."""

    def __init__(self, takes=lambda value: value, maxlength=None):
        self.value, self.events, self._takes, self._maxlength = "", [], takes, maxlength

    def fill(self, value):
        self.value = self._takes(value) if value else ""
        self.events.append("input")

    def press_sequentially(self, text):
        self.value += text
        self.events += ["keydown", "input", "keyup"] * len(text)

    def dispatch_event(self, kind):
        self.events.append(kind)

    def input_value(self):
        return self.value

    def get_attribute(self, name):
        return self._maxlength if name == "maxlength" else None


def test_eight_boxes_each_take_one_character_with_its_case_and_the_events_react_hears():
    """Fault: the whole code goes into the first box (one character lands), a character's case changes, or a box
    gets no input or change event, so the form's own state never holds it and its Submit stays disabled."""
    boxes = [Box() for _ in CODE]

    assert code_box.put(boxes, CODE) == ""
    assert [b.value for b in boxes] == list(CODE)
    assert all(b.events[:2] == ["input", "change"] for b in boxes)


def test_a_box_that_heeds_only_keys_is_typed_into():
    """Fault: a box the fill left empty (a form that listens to keys only) is read as done, or never typed into."""
    boxes = [Box() for _ in CODE]
    boxes[3] = Box(takes=lambda value: "")

    assert code_box.put(boxes, CODE) == ""
    assert boxes[3].value == "b" and "keydown" in boxes[3].events


def test_a_box_that_shows_another_character_is_never_sent():
    """Fault: a box that changed the code (lowercased it) passes the read-back, and Submit is pressed on a wrong code."""
    boxes = [Box(takes=str.lower) for _ in CODE]
    for box in boxes:
        box.press_sequentially = lambda text, box=box: setattr(box, "value", text.lower())

    said = code_box.put(boxes, CODE)
    assert said == code_box.SHOWS_OTHER.format(box=1)
    assert "oxnbtpni" not in said.casefold()  # the code is never in what the window and the command show


@pytest.mark.parametrize("boxes, code", [(8, "OxNbtPn"), (6, CODE)])
def test_a_code_that_doesnt_fit_the_field_goes_in_nowhere(boxes, code):
    """Fault: a code longer or shorter than the boxes is spread over them anyway."""
    field = [Box() for _ in range(boxes)]

    assert code_box.put(field, code) == code_box.DOESNT_FIT.format(boxes=boxes, chars=len(code))
    assert all(b.value == "" and not b.events for b in field)


def test_one_box_takes_the_whole_code_unless_it_is_too_short_for_it():
    """Fault: a single code box gets only the first character, or a box too short for the code gets a cut one."""
    one = Box()
    assert code_box.put([one], CODE) == "" and one.value == CODE
    assert code_box.put([Box(maxlength="6")], CODE) == code_box.DOESNT_FIT.format(boxes=1, chars=8)


@pytest.mark.parametrize("given, kept", [(" OxNb tPnI\n", CODE), ("12345678", "12345678"), ("Ox-Nb", ""), ("abc", ""),
                                         ("", "")])
def test_a_given_code_loses_only_its_spaces(given, kept):
    """Fault: a pasted code's case changes, or punctuation or a too-short code is taken as one."""
    assert code_box.given(given) == kept


class Words:
    """A frame whose visible text is `text`: get_by_text(pattern).first.is_visible() as Playwright answers it."""

    def __init__(self, text):
        self.text = text

    def get_by_text(self, pattern):
        shows = bool(pattern.search(self.text))
        return type("Found", (), {"first": type("First", (), {"is_visible": lambda self: shows})()})()


class Page:
    def __init__(self, *frames):
        self.frames = list(frames)


@pytest.mark.parametrize("words, said", [
    ("Incorrect security code", True), ("The verification code you entered is invalid", True),
    ("Invalid postal code", False), ("Promo code expired", False), ("Thank you for applying", False)])
def test_a_wrong_code_is_read_in_any_frame_and_no_other_code_is_one(words, said):
    """Fault: a wrong code on a form embedded in a company's page goes unseen (only the top frame read), or a postal
    or promo code's error reads as the emailed code's."""
    assert code_box.wrong(Page(Words("Acme careers"), Words(words))) is said
