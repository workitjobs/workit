'''
a student's Answer bank (W11 of docs/desktop_application_auto_apply.md): the
one-off questions they or their Claude answered once, which WorkIt Auto Apply
and the WorkIt extension fill again on any later form.
ex: {"are you open to working in person?": {"question": "Are you open to
working in person?", "answer": "Yes"}}
models/CLAUDE.md, "The Answer bank", has the design.
'''
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import BaseModel


class Answer_Bank(BaseModel):
    '''
    one row per student. `answers` maps a question's folded wording (the
    Fill engine's match: case, spacing, curly quotes and a trailing asterisk
    don't count) to {"question", "answer", "review"?, "options"?}: the
    question as a form words it, the answer (a string, or a list of the
    options picked; [] is "none of these"), `review: true` only on a Claude
    answer the student hasn't reviewed, and `options` only on the student's
    own pick from one list, which then answers only that list
    (models/CLAUDE.md, "The Answer bank").

    Its own table, not a column of applicant_profiles: every profile read
    loads that row's JSONB columns, and a bank grows to hundreds of KB.
    Merged a key at a time (queries/answer_banks.py), never replaced whole
    from a caller's copy. `version` goes up by one on every write: a reader
    asks with the version it holds and gets 304 when nothing changed.
    '''
    __tablename__ = "answer_banks"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __table_args__ = (
        # A reader looks keys up; an array or a string here would answer nothing and say nothing.
        CheckConstraint("jsonb_typeof(answers) = 'object'", name="answer_banks_answers_object"),
    )
