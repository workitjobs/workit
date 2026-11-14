"""WorkIt Auto Apply's Model route shapes (KAN-723, routers/apply_app.py).

A call is Apply's own `ask`: a system prompt, a prompt and the JSON schema
its answer must fit. The schema is checked here, before anything is counted
or sent: it must be a valid JSON Schema for an object, at most MAX_SCHEMA
characters and MAX_DEPTH levels, with none of the REFUSED keywords (Apply's
schemas use none). The check is by key, so a property may not have one of
those names either."""

import datetime
import json
from typing import Any, Literal

from jsonschema import Draft202012Validator, SchemaError
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Characters. Apply's lean prompts fit Groq's 8,000 tokens a minute (about
# 32,000 characters); a Developer checkout's full ones run past 45,000.
MAX_TEXT = 100_000
MAX_SCHEMA = 20_000
# Levels of objects and arrays. Apply's schemas use under ten; at about 150,
# jsonschema's own check runs out of Python's stack (a 500).
MAX_DEPTH = 32

# `$ref` and its dynamic forms: jsonschema resolves them, fetching a remote
# one's URL by default, and a recursive one runs as deep as the answer.
# `pattern` and `patternProperties`: the answer's check runs them with
# Python's backtracking `re`, in the API's event loop, and `^(a+)+$` on 40
# characters takes hours, for every user at once.
REFUSED = frozenset({"$ref", "$dynamicRef", "$recursiveRef", "pattern", "patternProperties"})


def _refuse_keywords(value: Any, depth: int = 1) -> None:
    if not isinstance(value, dict | list):
        return
    if depth > MAX_DEPTH:
        raise ValueError(f"the schema is nested more than {MAX_DEPTH} levels deep")
    if isinstance(value, dict):
        if found := REFUSED & value.keys():
            raise ValueError(f"the schema may not use {', '.join(sorted(found))}")
        value = value.values()
    for item in value:
        _refuse_keywords(item, depth + 1)


class ModelCall(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # What the call is for (an essay, a check), for the logs and W13's counts.
    kind: str = Field(default="ask", pattern=r"^[a-z][a-z0-9_]{0,39}$")
    # Apply's model tier; the route maps it to a size of the API's model chain.
    model: Literal["haiku", "sonnet", "opus"]
    system: str = Field(default="", max_length=MAX_TEXT)
    prompt: str = Field(min_length=1, max_length=MAX_TEXT)
    # `schema` on the wire; BaseModel has a `schema` of its own.
    answer_schema: dict[str, Any] = Field(alias="schema")

    @field_validator("answer_schema")
    @classmethod
    def _checked(cls, schema: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(schema)) > MAX_SCHEMA:
            raise ValueError(f"the schema is over {MAX_SCHEMA} characters")
        if schema.get("type") != "object":
            raise ValueError('the schema must be for an object ("type": "object")')
        _refuse_keywords(schema)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            raise ValueError(f"the schema is not valid JSON Schema: {e.message}") from None
        return schema


class Usage(BaseModel):
    """The student's model use this month, in tokens, against the cap."""

    used: int
    cap: int
    resets_at: datetime.datetime


class ModelAnswer(BaseModel):
    answer: dict[str, Any]
    # Tokens this call spent, every provider tried included.
    tokens: int
    usage: Usage
