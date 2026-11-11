"""
Upload fills the profile from the resume's header (KAN-436).

An uploaded resume's header (`resume_parser.read_header`, rules only, never
a model) fills the profile's **empty** fields: the contact email, phone,
location, LinkedIn, GitHub, Portfolio and Other links, and the resume
header's Additional line. **A value is never overwritten.** One that
differs from the profile's comes back as an offer, which the upload's note
shows with Use This; the student decides. Free text and links with no free
field go to the Additional line, joined with " | ", only when that line is
empty and the text fits; otherwise the note says there was more than fits.

    plan(profile, reading) -> HeaderFill     pure: what to add and offer
    fill_from_header(session, applicant_id, raw_text) -> HeaderFill
                                              plans and writes the adds

Every value passes My Profile's own check (`ApplicantProfileUpdate`)
before it is added or offered, so a link that is no web address, or a
value over a column's length, is left out.
"""

import re
import uuid
from collections.abc import Mapping

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import Applicant_Profile
from app.schemas.profile import (
    RESUME_HEADER_EXTRA_MAX,
    ApplicantProfileUpdate,
    HeaderFill,
    HeaderOffer,
)
from app.utils.resume_parser import HeaderReading, read_header

# The profile's columns the header fills, in the note's order
FIELDS = (
    "contact_email", "phone_number", "location", "linkedin_url", "github_url", "portfolio_url", "other_url",
    "resume_header_extra",
)
LINK_FIELDS = ("linkedin_url", "github_url", "portfolio_url", "other_url")
# A link with no field of its own takes the first free one of these
_OTHER_LINKS = ("portfolio_url", "other_url")


def _checked(field: str, value: str) -> str | None:
    """The value as My Profile would save it ("https://" on a link), or None
    when My Profile would refuse it."""
    try:
        return getattr(ApplicantProfileUpdate.model_validate({field: value}), field)
    except ValidationError:
        return None


def _key(field: str, value: str | None) -> str:
    """What two values are compared by: a phone's last ten digits, a link
    without its scheme, "www." or a trailing slash, any other in any case."""
    if not value:
        return ""
    if field == "phone_number":
        return re.sub(r"\D", "", value)[-10:]
    if field in LINK_FIELDS:
        value = re.sub(r"^(?:https?://)?(?:www\.)?", "", value.strip(), flags=re.IGNORECASE).rstrip("/")
    return " ".join(value.casefold().split())


def plan(profile: Mapping[str, str | None], reading: HeaderReading, sign_in_email: str | None = None) -> HeaderFill:
    """What the header adds to the profile and what it offers. `profile`
    holds the current value of each of FIELDS."""
    now = {field: profile.get(field) for field in FIELDS}
    fill = HeaderFill()

    def give(field: str, value: str | None) -> bool:
        """Adds the value to an empty field or offers it beside a different
        one; False when it is not one My Profile would save."""
        checked = value and _checked(field, value)
        if not checked:
            return False
        if not now[field]:
            now[field] = fill.added[field] = checked
        elif _key(field, now[field]) != _key(field, checked):
            fill.offers.append(HeaderOffer(field=field, value=checked))
        return True

    # The sign-in email is what an empty contact email already means
    if reading.email and _key("contact_email", reading.email) != _key("contact_email", sign_in_email):
        give("contact_email", reading.email)
    give("phone_number", reading.phone)
    give("location", reading.location)
    give("linkedin_url", reading.linkedin)
    give("github_url", reading.github)

    left: list[str] = []
    for url in reading.links:
        if any(_key(f, now[f]) == _key(f, url) for f in LINK_FIELDS):
            continue
        if _checked("other_url", url) is None:
            continue  # no web address, wherever it would go
        free = next((f for f in _OTHER_LINKS if not now[f]), None)
        if free is None:
            # No free field: the link joins the Additional line, as printed
            left.append(re.sub(r"^(?:https?://)?(?:www\.)?", "", url, flags=re.IGNORECASE).rstrip("/"))
        else:
            give(free, url)

    text = " | ".join([*reading.text, *left])
    if text and _key("resume_header_extra", text) != _key("resume_header_extra", now["resume_header_extra"]):
        if len(text) > RESUME_HEADER_EXTRA_MAX:
            fill.overflow = True
        else:
            give("resume_header_extra", text)
    return fill


async def fill_from_header(session: AsyncSession, applicant_id: uuid.UUID, raw_text: str | None) -> HeaderFill:
    """Reads the upload's header and fills the profile's empty fields in
    this session; the caller commits it with the upload. Nothing when there
    is no text or no profile."""
    if not raw_text:
        return HeaderFill()
    profile = await session.get(Applicant_Profile, applicant_id)
    if profile is None:
        return HeaderFill()
    fill = plan({f: getattr(profile, f) for f in FIELDS}, read_header(raw_text), profile.email)
    for field, value in fill.added.items():
        setattr(profile, field, value)
    return fill
