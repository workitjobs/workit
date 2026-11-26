import datetime
import uuid

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Model_Usage(Base):
    """
    One student's model use through WorkIt Auto Apply's Model route in one
    day (UTC), for the daily Usage cap, and their calls in the current minute, for the per-minute limit
    (app/queries/model_usage.py, KAN-723). Goes with the account.
    """

    __tablename__ = "model_usage"

    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    input_tokens: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    # Calls sent to the providers, answered or not.
    calls: Mapped[int] = mapped_column(server_default=text("0"))
    # The minute the per-minute count is for, and the calls taken in it.
    minute: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    minute_calls: Mapped[int]
