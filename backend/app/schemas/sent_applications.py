"""
What an application sent (W11, routers/sent_applications.py): each question
and its answer, as WorkIt Auto Apply filled and read them back.
"""

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Text = Annotated[str, StringConstraints(max_length=20000)]  # an essay or a cover letter at most


class SentAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Question
    answer: Text | list[Text] = Field(union_mode="left_to_right")  # the options picked, for a multi-select
    ai: bool = False  # an answer AI wrote: an essay, or a one-off answer it drafted


class SentApplicationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The engine's 25 saved forms ask 10 to 60 questions; 300 is far past any of them.
    answers: list[SentAnswer] = Field(max_length=300)


class SentApplication(BaseModel):
    answers: list[SentAnswer]
    sent_at: datetime.datetime
