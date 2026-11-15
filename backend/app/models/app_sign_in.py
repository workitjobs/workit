import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class App_Sign_In(Base):
    """
    One sign-in of WorkIt Auto Apply (KAN-723, W5; app/services/app_sign_in.py
    is the one writer): the one-time code the website's /app-sign-in page asked
    for, bound to the app's PKCE challenge, and when the app traded it for a
    session. Only the code's sha256 is kept, and only for an hour. Goes with the
    account.
    """

    __tablename__ = "app_sign_ins"

    code_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"), index=True)
    # base64url(sha256(verifier)), RFC 7636's S256
    challenge: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NULL until the app trades the code, right verifier or not: a code goes once
    traded_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
