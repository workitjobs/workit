"""GET /admin/rules-anomalies' answer (KAN-772, services/rules_anomalies.py):
the accounts whose Rules table fetches look like scraping, each with the
reasons."""

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

Reason = Literal["many_systems", "fetch_without_fill", "regular_timing", "capped"]


class Flag(BaseModel):
    reason: Reason
    # The numbers behind it, in a sentence ("7 job systems within 30 minutes").
    detail: str


class FlaggedAccount(BaseModel):
    account_id: uuid.UUID
    fetches: int
    job_systems: list[str]
    fills: int
    # None for an account flagged only for minting tokens to the cap without fetching.
    first_fetch: datetime.datetime | None
    last_fetch: datetime.datetime | None
    flags: list[Flag]


class RulesAnomalies(BaseModel):
    days: int
    since: datetime.datetime
    accounts: list[FlaggedAccount]
