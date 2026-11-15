"""What every Auto Apply kind shares: its data's base model and field
types, what `build` returns, and the note on pronouns that ends each
system prompt (Apply's applicant.pronouns_note)."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# The placeholders Apply's prompts say. The app puts the name back into
# the answer (D8); the school is no personal data, so the server says it.
NAME, SCHOOL = "@NAME@", "@SCHOOL@"

MAX_SOURCES = 100_000  # characters: the Story bank, Stock answers and Company material together
MAX_ANSWER = 20_000  # characters of one draft or answer; a cover letter is under 5,000
MAX_LINE = 2_000  # characters of a question, a length or one flag
MAX_KEYS = 20  # answers or questions in one call; a form has fewer than ten

# A key names one answer in the schema the server builds ("q1", "d2"), so
# it is a plain name, never text the model reads as an instruction.
Key = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
Sources = Annotated[str, Field(max_length=MAX_SOURCES)]
Answer = Annotated[str, Field(max_length=MAX_ANSWER)]
Line = Annotated[str, Field(max_length=MAX_LINE)]


class Data(BaseModel):
    """The fields every kind takes. A kind's own model adds its fields; an
    unknown one is refused, so no request can add an instruction."""

    model_config = ConfigDict(extra="forbid")

    # As the profile states them ("she/her/hers", "ze/zir"): one short line, so it can't carry instructions.
    pronouns: str = Field(default="they/them/theirs", pattern=r"^[^\n\r<>{}]{1,40}$")
    school: str = Field(default="", max_length=200)


@dataclass(frozen=True)
class Built:
    system: str
    prompt: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class Kind:
    """One `ask` of Apply's, built on the server. `size` is the API's model
    chain (app/services/models.py): Apply's Opus and Sonnet calls run on the
    large one, its Haiku calls on the small one."""

    name: str
    version: int
    data: type[Data]
    size: Literal["large", "small"]
    build: Callable[[Any], Built]
    # Said as the applicant (the pronouns note, the school named), as Apply's
    # as_applicant wraps the calls of essays.py and the Pre-submit review.
    applicant: bool = True


def pronouns_note(pronouns: str) -> str:
    return (f"\n\n{NAME}'s pronouns are {pronouns}. Wherever you write about {NAME} in the third person "
            "(a plan, a note, a reason), use these pronouns only.")


def said(built: Built, data: Data) -> Built:
    """`built` as Apply's as_applicant said every call: the pronouns note on
    the system prompt and the school named, in the schema too; the name
    stays NAME."""
    school = data.school.strip() or "their school"
    in_json = json.dumps(school)[1:-1]
    return Built(
        (built.system + pronouns_note(data.pronouns)).replace(SCHOOL, school),
        built.prompt.replace(SCHOOL, school),
        json.loads(json.dumps(built.schema).replace(SCHOOL, in_json)),
    )
