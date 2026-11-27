"""A code step after Lisul's Submit (D9): the field a job system shows for the code it emailed (Greenhouse's
security code). Here, not in apply.email_code, which reads the code from Gmail: the Student build reads no mail
(apply.build, KAN-855), yet still sees the field come and tells the student to type the code.

The code field is one that shows after his press and was not on the form when Apply handed him the page (so a
postal code box is never one), with each of its boxes empty (he did not type the code himself).

When the student gives the code instead (the card's code box or `apply window code`), `put` enters it on the
held page with locator actions only, so it works on a plain Worker's page too: one character per box, read
back before the run presses Submit again.
"""

import re
from collections.abc import Callable

from apply import account_pages, captcha, greenhouse, upload_origin
from apply.page_functions import WORDS

# Greenhouse's code boxes first, then any box a code goes in.
FIELDS = f"{greenhouse.SECURITY_BOXES}, {greenhouse.SECURITY_BOX}, {account_pages.CODE_BOX}"
# A box whose words name another code, which is never an emailed one.
NOT_A_CODE = re.compile(r"zip|postal|post_code|country|area|promo|coupon|discount|referr|invite|dial", re.IGNORECASE)


def boxes(page) -> list:
    """Every visible box a code could go in, in the first frame that has one,
    as (a key that names it, its locator). Never a captcha's frame, where Apply puts no code, nor another site's
    (upload_origin's frame rule, KAN-855's second review): its box is never the job site's code."""
    for n, frame in enumerate(page.frames):
        if n and (captcha.in_frame(frame.url) or not upload_origin.frame_may_upload(frame)):
            continue
        try:
            found = []
            for box in frame.locator(FIELDS).all():
                words = box.evaluate(WORDS)
                if box.is_visible() and not NOT_A_CODE.search(words):
                    found.append((f"{n}|{words}", box))
        except Exception:
            continue  # a frame gone or going
        if found:
            return found
    return []


def new_boxes(page, form: set[str]) -> list:
    """The code field that came after the form (`form`: the keys of its own boxes): its visible boxes, each empty."""
    came = [(key, box) for key, box in boxes(page) if key not in form]
    try:
        return came if came and all(not box.input_value() for _, box in came) else []
    except Exception:
        return []


class TypeTheCode:
    """The Student build's watch of one held page for a code step after each press of the student's, as
    apply.email_code.EmailCode watches it (`pressed`, `tick`), with no mail: once the code field comes, `tell`
    puts "needs code" and `why` in the Apply window, once a press. Apply types nothing."""

    def __init__(self, tell: Callable[[str, str], None], why: str):
        self._tell, self._why = tell, why
        self._form: set[str] | None = None  # the code-like boxes on the form as Apply handed it over
        self._pressed = False

    def pressed(self, words: str = "") -> None:
        self._pressed = True

    def tick(self, page) -> None:
        if self._form is None:
            self._form = {key for key, _ in boxes(page)}
        elif self._pressed and new_boxes(page, self._form):
            self._pressed = False
            self._tell("needs code", self._why)


# The code the student (or `apply window code`) gives for the field: case kept, as Greenhouse's codes are
# case-sensitive letters and digits ("OxNbtPnI").
CODE = re.compile(r"^[A-Za-z0-9]{4,12}$")
# What a job site says when the code is wrong: Greenhouse's "Incorrect security code".
_EMAILED = r"\b(?:security|verification|confirmation|access|one-time)\s+code\b"  # never a postal or promo code
WRONG = re.compile(rf"\b(?:incorrect|invalid|wrong|expired)\b[^.\n]{{0,20}}{_EMAILED}|{_EMAILED}[^.\n]{{0,30}}"
                   r"\b(?:incorrect|invalid|wrong|expired|doesn.t match|did not match)\b", re.IGNORECASE)

NOT_A_CODE_GIVEN = "That isn't a code: give the letters and digits from the email, as they are (case counts)."
NO_FIELD = "The form shows no code field now, so Apply entered nothing. Read the state, or open the form."
NOT_SENT_YET = "Submit wasn't pressed on this form yet: the job site asks for its code only after Submit."
DOESNT_FIT = "The code field has {boxes} boxes, and the code has {chars} characters, so Apply entered nothing."
NOT_ENTERED = "The code field changed while Apply entered the code, so it pressed nothing. Open the form to check it."
SHOWS_OTHER = ("Box {box} of the code field shows another character than the code given, so Apply pressed nothing. "
               "Open the form and enter it yourself.")
WRONG_CODE = "The job site says the code is wrong: check the newest email from it, and enter that code."
NO_ANSWER = ("Apply entered the code and pressed Submit, but the job site didn't show that it went in. Open the form "
             "to see what it says.")


def given(code: str) -> str:
    """The code as given, without the spaces a paste brings; "" when it is no code."""
    code = "".join(str(code or "").split())
    return code if CODE.match(code) else ""


def put(boxes: list, code: str) -> str:
    """Enter `code` into a code field's `boxes`: one character a box where it has a box per character (Greenhouse's
    eight), else the whole code in the one box. Each box is filled as the student's typing fills it: Playwright's
    fill sets its value and sends the `input` event a React form listens for, and then `change`. A box that doesn't
    take its character so (a form that heeds only keys) is typed into key by key. Every box is read back: "" when
    each holds its character exactly, case and all; else why not, and the caller presses nothing."""
    parts = list(code) if len(boxes) > 1 else [code]
    if len(boxes) > 1 and len(boxes) != len(code):
        return DOESNT_FIT.format(boxes=len(boxes), chars=len(code))
    if len(boxes) == 1:
        limit = boxes[0].get_attribute("maxlength")
        if limit and limit.isdigit() and 0 < int(limit) < len(code):
            return DOESNT_FIT.format(boxes=1, chars=len(code))
    for box, part in zip(boxes, parts):
        box.fill(part)
        box.dispatch_event("change")
    for box, part in zip(boxes, parts):
        if box.input_value() != part:
            box.fill("")
            box.press_sequentially(part)
            box.dispatch_event("change")
    off = next((n for n, (box, part) in enumerate(zip(boxes, parts), 1) if box.input_value() != part), 0)
    return SHOWS_OTHER.format(box=off) if off else ""  # which box, never what it shows: that is the code


def code_field(page) -> list:
    """The code field's boxes on the page now: Greenhouse's own first, else any box a code goes in (`boxes`)."""
    for frame in page.frames:
        try:
            own = [box for box in frame.locator(greenhouse.SECURITY_BOXES).all() if box.is_visible()]
        except Exception:
            continue
        if own:
            return own
    return [box for _, box in boxes(page)]


def wrong(page) -> bool:
    """Whether the page says the code entered is wrong ("Incorrect security code")."""
    for frame in page.frames:  # an embedded form's words are in its own frame, as its boxes are (code_field)
        try:
            if frame.get_by_text(WRONG).first.is_visible():
                return True
        except Exception:
            continue
    return False
