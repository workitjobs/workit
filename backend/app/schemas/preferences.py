"""
A seeker's saved job preferences, for GET and PUT
/applicants/{applicant_id}/preferences (routers/preferences.py).

THE FIELDS ARE GET /jobs' QUERY PARAMETERS, names and values alike (`location`,
`work_style`, `role`...; routers/jobs.py read_filters), so the frontend turns a
saved set straight into the Jobs page's filters and back with the one mapping
it already has (frontend/src/app/(seeker)/jobs/filter-query.ts). The caps
match read_filters' too. Date Posted is left out on purpose: a saved "past 24
hours" would empty the feed within days, so it stays a per-visit filter.
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.models import dto
from app.schemas.jobs import (
    MAX_CUSTOM_ROLES,
    CustomRole,
    JobTypeKey,
    PlaceCode,
    RoleSlug,
    SeasonKey,
)

# Above any posting's pay, as GET /jobs caps ?min_pay=.
_MAX_PAY = 10_000_000
# Exact in the column (numeric), a plain number in JSON: Pydantic sends a
# Decimal as a string ("45.00") by default, which the frontend would read as text.
Pay = Annotated[
    Decimal,
    Field(gt=0, le=_MAX_PAY, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


class JobPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: list[PlaceCode] = Field(default_factory=list, max_length=60)
    work_style: list[dto.work_style] = Field(default_factory=list, max_length=3)
    role: list[RoleSlug] = Field(default_factory=list, max_length=60)
    # Roles the student typed that `role` can't hold (2026-11-16): any of
    # these or of `role` keeps a job, as GET /jobs' ?custom_role= does.
    custom_role: list[CustomRole] = Field(default_factory=list, max_length=MAX_CUSTOM_ROLES)
    experience: list[Literal["student", "new_grad", "experienced"]] = Field(
        default_factory=list, max_length=3
    )
    job_type: list[JobTypeKey] = Field(default_factory=list, max_length=4)
    min_pay: Pay | None = None
    max_pay: Pay | None = None
    pay_per: Literal["hour", "year"] = "year"
    start_term: list[SeasonKey] = Field(default_factory=list, max_length=12)
    visa: Literal["sponsors"] | None = None

    @model_validator(mode="after")
    def _tidy(self) -> "JobPreferences":
        # Each pick once, in the order given; a range typed backwards is the
        # range meant, as read_filters reads it.
        for name in ("location", "work_style", "role", "experience", "job_type", "start_term"):
            setattr(self, name, list(dict.fromkeys(getattr(self, name))))
        # A custom role once, ignoring case: "UX Researcher" and "ux
        # researcher" find the same titles. The first spelling is kept.
        seen: set[str] = set()
        kept: list[str] = []
        for typed in self.custom_role:
            if typed.casefold() not in seen:
                seen.add(typed.casefold())
                kept.append(typed)
        self.custom_role = kept
        if self.min_pay is not None and self.max_pay is not None and self.min_pay > self.max_pay:
            self.min_pay, self.max_pay = self.max_pay, self.min_pay
        return self
