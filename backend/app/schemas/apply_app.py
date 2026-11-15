"""WorkIt Auto Apply's Model route shapes (KAN-723, routers/apply_app.py).

A call is one of Apply's `ask`s by its kind: the server builds the prompt and
the schema from the call's data (app/apply_prompts/, D5), so no request
carries a prompt or a schema. The free-form call that did, with its schema
checks, went once every kind was built on the server (2026-11-14)."""

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AskCall(BaseModel):
    """One of Apply's calls by its kind (app/apply_prompts/): the server
    builds its prompt and schema from `data`, which the kind's own model
    checks."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}(?:\.[a-z][a-z0-9_]{0,39})?$")
    version: int = Field(default=1, ge=1, le=1000)
    data: dict[str, Any]


class Usage(BaseModel):
    """The student's model use today (UTC), in tokens, against the cap."""

    used: int
    cap: int
    resets_at: datetime.datetime


class ModelAnswer(BaseModel):
    answer: dict[str, Any]
    # Tokens this call spent, every provider tried included.
    tokens: int
    usage: Usage
