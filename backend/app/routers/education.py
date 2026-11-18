"""Suggestions for the Education form as a student types (2026-11-17).

    GET /education/schools?q=
        Up to eight schools whose name or alias the words lead or hold, best
        first, each with its place ("Stony Brook, NY", or a country).

    GET /education/fields?q=
        Up to eight fields of study, from the US Department of Education's
        CIP list ("Computer Science", "Economics").

Under two letters, either answers an empty list. Both need a sign-in, as every
student route does, though the lists are public data: an open route would
serve them to anyone scraping. They write nothing and spend no use. The lists
and their search are `services/education_lists.py`; the form keeps whatever
the student types, so neither route checks a saved value.
"""

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_account
from app.schemas.auth import AuthenticatedAccount
from app.schemas.education import EducationSuggestion
from app.services.education_lists import search_fields, search_schools

router = APIRouter(prefix="/education")


@router.get("/schools", response_model=list[EducationSuggestion])
async def schools(
    q: str = Query("", max_length=120),
    _account: AuthenticatedAccount = Depends(get_current_account),
) -> list[EducationSuggestion]:
    return [EducationSuggestion(name=s.name, place=s.place) for s in search_schools(q)]


@router.get("/fields", response_model=list[EducationSuggestion])
async def fields(
    q: str = Query("", max_length=120),
    _account: AuthenticatedAccount = Depends(get_current_account),
) -> list[EducationSuggestion]:
    return [EducationSuggestion(name=s.name) for s in search_fields(q)]
