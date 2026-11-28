"""
Which of WorkIt's own fields a fact of the Fill engine's belongs in (W11):
WorkIt Auto Apply's Needs you answers a fact the engine names by its key
("logistics.willing_to_relocate_for_summer"), and one that a field of the
website holds (Application Info's Application answers, My Profile's phone
and links) is saved in that field, so the website shows it where the
student answers it, and the extension fills it as it fills that field.

There is no second mapping to keep in step: each field the student hasn't
answered is tried through WorkIt's own one (`engine_profile.workit_profile`,
the extension's port), and the field that makes the engine's profile hold
the fact is the one. A field with options takes the option that gives the
fact's value; a field of text, the fact itself, checked as the website's
own save checks it (`AutofillAnswers`, `ApplicantProfileUpdate`), and only
when the key holds that field's own value (`PROBE`). A list
field never takes one typed answer, and a field the student answered is
never written over: the fact then stays in `fill_profile`.

Pure: it takes the student as `queries/engine_student.py` reads them.
"""

from typing import Any, Literal, get_args, get_origin

from pydantic import ValidationError

from app.schemas.autofill_answers import AutofillAnswers
from app.schemas.profile import ApplicantProfileUpdate
from app.services.engine_profile import workit_profile

# My Profile's fields a fact can go into: the phone and the links. The name, email and location are the student's
# from sign-up and My Profile, so the engine never asks them; `other_url` only stands in for a portfolio link.
PROFILE_FIELDS = ("phone_number", "linkedin_url", "github_url", "portfolio_url")


def workit_field(student: dict, today: str, key: str, value: Any) -> tuple[str, str, Any] | None:
    """Where WorkIt's own fields keep `value` at the engine's `key`: ("answers" or "profile", the field, the value
    to save there), or None when no field the student left unanswered gives it."""
    path = key.split(".")
    if _at(workit_profile(student, today), path) is not None:
        return None  # a WorkIt field holds the key already, and wins on every form
    for where, field, saved, exact in _candidates(student, value):
        got = _at(workit_profile(_with(student, where, field, saved), today), path)
        if got is None:
            continue
        if exact and _same(got, value):
            return where, field, saved
        # A text field's own value must be what the key holds: an address line fills the home's city from the
        # profile's location, so a city typed for "City" would otherwise land in Address Line 1.
        if not exact and _same(got, saved) and _at(workit_profile(_with(student, where, field, PROBE), today),
                                                   path) == PROBE:
            return where, field, saved
    return None


PROBE = "\x00workit field probe"  # a value no student types, run through the mapping only, never saved


def _with(student: dict, where: str, field: str, value: Any) -> dict:
    """The student with `value` in one field of theirs."""
    if where == "answers":
        return {**student, "answers": {**(student.get("answers") or {}), field: value}}
    return {**student, field: value}


def _candidates(student: dict, value: Any):
    """Each unanswered field and the value to try in it: every option of a field with options (`exact`: it must give
    the fact's value), else the fact itself as the website's save takes it."""
    answers = student.get("answers") or {}
    for field, info in AutofillAnswers.model_fields.items():
        if answers.get(field) is not None:
            continue
        kinds = [a for a in get_args(info.annotation) if a is not type(None)] or [info.annotation]
        if any(get_origin(k) is list for k in kinds):
            continue
        options = [o for k in kinds if get_origin(k) is Literal for o in get_args(k)]
        if options:
            yield from (("answers", field, option, True) for option in options)
        elif (saved := _checked(AutofillAnswers, field, value)) is not None:
            yield "answers", field, saved, False
    for field in PROFILE_FIELDS:
        if not student.get(field) and (saved := _checked(ApplicantProfileUpdate, field, value)) is not None:
            yield "profile", field, saved, False


def _checked(model: type, field: str, value: Any) -> Any:
    """`value` as the website's own save keeps `field`, or None when that save would refuse it."""
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        return None
    try:
        return getattr(model.model_validate({field: value}), field)
    except ValidationError:
        return None


def _at(tree: Any, path: list[str]) -> Any:
    """The value at `path`, or None when nothing (or nothing but empty values) is there."""
    for key in path:
        tree = tree.get(key) if isinstance(tree, dict) else None
    return None if tree in (None, "", [], {}) else tree


def _same(got: Any, value: Any) -> bool:
    """A form's words match in any case ("he/him" is "He/him"); anything else must be the same value."""
    if isinstance(got, str) and isinstance(value, str):
        return got.strip().casefold() == value.strip().casefold()
    return type(got) is type(value) and got == value
