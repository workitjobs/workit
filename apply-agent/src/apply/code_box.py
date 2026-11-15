"""A code step after Lisul's Submit (D9): the field a job system shows for the code it emailed (Greenhouse's
security code). Here, not in apply.email_code, which reads the code from Gmail: the Student build reads no mail
(apply.build, KAN-855), yet still sees the field come and tells the student to type the code.

The code field is one that shows after his press and was not on the form when Apply handed him the page (so a
postal code box is never one), with each of its boxes empty (he did not type the code himself).
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
