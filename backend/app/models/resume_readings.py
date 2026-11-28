import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Which route read the upload: Upload, the parse preview, Import Updated
# Resume and Import Again (services/resume_reading.py's `read_upload`).
ROUTES = ("upload", "preview", "update", "import_again")
# Why the parser's reading was saved (bank_import.read_resume): no text to
# read, no AI reading left today, no model answered (down, out of quota or
# the request too large), the model ran past MODEL_WAIT_SECONDS, its reply
# failed the schema, or the text backed none of its entries.
PARSER_REASONS = ("no_text", "no_uses_left", "model_unavailable", "timeout", "wrong_shape", "nothing_backed")
# The `model` column's length; the writer clips a longer name to it.
MODEL_NAME_LENGTH = 100


class Resume_Reading(Base):
    """
    One reading of an uploaded resume (KAN-898): who read it (the model or
    the parser), and when the parser's reading was saved, why; how long it
    took, how many entries and skills it found, and how many of the
    model's fields the check against the resume's text dropped. So the
    team sees how often production falls back to the parser (KAN-806).
    **Never the resume's text, a name or any field's value**: only the
    account, the route, the reader, a reason and counts. Written with the
    route's other writes, so a failed save keeps none; the preview commits
    it alone, as it commits its AI use. Kept 90 days
    (services/retention.py), and deleted with the account.

    The text columns have no CHECK on purpose: the row commits with the
    student's upload, so a value the database refused would fail the
    upload, and KAN-806 can add a reason with no migration. Only code
    writes them, from ROUTES and PARSER_REASONS above.
    """

    __tablename__ = "resume_readings"
    __table_args__ = (
        Index("ix_resume_readings_created_at", "created_at"),
        Index("ix_resume_readings_applicant_id", "applicant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    applicant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applicant_profiles.id", ondelete="CASCADE"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    route: Mapped[str] = mapped_column(String(16))
    # "model" or "parser"
    read_by: Mapped[str] = mapped_column(String(8))
    # Null when the model's reading was saved; else one of PARSER_REASONS.
    reason: Mapped[str | None] = mapped_column(String(24))
    duration_ms: Mapped[int] = mapped_column(Integer)
    entries: Mapped[int] = mapped_column(Integer)
    skills: Mapped[int] = mapped_column(Integer)
    # The model's fields the check against the text dropped (bank_import's
    # `_backed`): text fields, bullets, courses, tools, an entry's dates, a
    # GPA, and skills. Null when no reply came back to check.
    fields_dropped: Mapped[int | None] = mapped_column(Integer)
    # The model that replied, as the chain names it ("gemini-3.5-flash-lite"),
    # and the tokens its reply cost: read (the prompt) and written (the
    # reply, reasoning included). KAN-955. Null when no model replied: the
    # parser read alone, or every endpoint failed or stalled. Set for a
    # reply that failed the schema or backed nothing, since it was paid for.
    # Tokens an endpoint spent before it failed are not known or counted.
    model: Mapped[str | None] = mapped_column(String(MODEL_NAME_LENGTH))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
