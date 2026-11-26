import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.db import Base


class Apply_Report(Base):
    """
    A report a student sent from WorkIt Auto Apply's support form (D26, KAN-837, app/routers/apply_reports.py): its
    category, their own words and whether WorkIt may email them, and, when they included one Application, its
    Record as the app keeps it (the answers, the essays, the form's screenshots) and its Trace with the student's
    private values masked in the app. Only ever sent on a press, never automatically. It has no retention period: the team deletes it once its problem is fixed, as the privacy
    policy says (DELETE /admin/apply-reports/{id}). It goes with the account.
    """

    __tablename__ = "apply_reports"
    __table_args__ = (
        CheckConstraint("category IN ('form', 'answer', 'sign_in', 'app', 'other')", name="apply_reports_category_check"),
        Index("ix_apply_reports_created_at", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(16))  # schemas' Category
    contact_ok: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # Apply's id for the Application (its Tracker row), and what the row names; '' for a general question.
    application_id: Mapped[str] = mapped_column(String(200), server_default="")
    company: Mapped[str] = mapped_column(Text, server_default="")
    role: Mapped[str] = mapped_column(Text, server_default="")
    posting_url: Mapped[str] = mapped_column(Text, server_default="")
    # The Application's status in the app when it was sent (held, failed, handoff...).
    outcome: Mapped[str] = mapped_column(String(40), server_default="")
    note: Mapped[str] = mapped_column(Text, server_default="")
    # The Record's text files by name (answers.json, essays.md...: schemas' TEXT_FILES).
    files: Mapped[dict] = deferred(mapped_column(JSONB, server_default=text("'{}'::jsonb")))
    form_png: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    after_submit_png: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    # The Trace's JSON lines, masked in the app (apply.report).
    trace: Mapped[str] = deferred(mapped_column(Text, server_default=""))
