"""The Education form's suggestions (services/education_lists.py and
GET /education/schools, /education/fields): the committed lists, searched."""

import uuid

import httpx
import pytest

from app.deps import get_current_account
from app.main import app
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services.education_lists import fold, search_fields, search_schools

pytestmark = pytest.mark.anyio


def names(suggestions):
    return [s.name for s in suggestions]


def test_fold_drops_accents_case_and_punctuation():
    assert fold("Université  Laval") == "universite laval"
    assert fold("St. John's") == "st john s"


def test_a_school_is_found_by_its_start_its_words_or_an_alias():
    assert names(search_schools("stony brook"))[0] == "Stony Brook University"
    assert names(search_schools("brook stony"))[0] == "Stony Brook University"
    assert "Stony Brook University" in names(search_schools("suny stony"))


def test_a_school_carries_its_place():
    top = search_schools("stony brook")[0]
    assert top.place == "Stony Brook, NY"


def test_schools_outside_the_us_are_listed_with_their_country():
    toronto = [s for s in search_schools("university of toronto") if s.name == "University of Toronto"]
    assert toronto and toronto[0].place.endswith("Canada")


def test_a_field_of_study_reads_as_a_student_says_it():
    assert names(search_fields("computer sci"))[0] == "Computer Science"
    # CIP's ", General" is dropped and its ", Other" rows are left out.
    assert "Economics" in names(search_fields("economics"))
    assert not any(n.endswith("Other") for n in names(search_fields("computer")))


def test_one_letter_suggests_nothing_and_the_list_is_short():
    assert search_schools("s") == []
    assert len(search_schools("university")) == 8


async def test_the_routes_need_a_sign_in_and_answer_the_lists():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/education/schools", params={"q": "stony"})).status_code == 401
        app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
            id=uuid.uuid4(), email="sam@example.com", full_name="Sam Seeker",
            account_type=AccountType.APPLICANT, onboarding_completed=True,
        )
        try:
            schools = (await client.get("/education/schools", params={"q": "stony brook"})).json()
            fields = (await client.get("/education/fields", params={"q": "econ"})).json()
        finally:
            app.dependency_overrides.pop(get_current_account, None)
    assert schools[0] == {"name": "Stony Brook University", "place": "Stony Brook, NY"}
    assert fields[0]["name"] == "Economics" and fields[0]["place"] is None
