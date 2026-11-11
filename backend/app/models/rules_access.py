import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Rules_Token(Base):
    """
    A site token (KAN-756, routers/extension_rules.py): it fetches one job
    system's Rules table, for one account, until `expires_at` (a few
    minutes). Only its sha256 is kept, as the connector's tokens, so a leaked
    table fetches nothing. Purged a day after it is made
    (services/retention.py). Goes with the account.
    """

    __tablename__ = "rules_tokens"
    __table_args__ = (Index("ix_rules_tokens_created_at", "created_at"),)

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"))
    job_system: Mapped[str] = mapped_column(String(24))
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rules_Fetch(Base):
    """
    One fetch of a job system's Rules table (KAN-756): which account, which
    job system, when. For anomaly review (an account pulling every system,
    or fetching without filling) and for naming the account a leaked table
    was served to (services/rules_watermark.py trace). Kept 90 days, as
    fill events. Goes with the account.
    """

    __tablename__ = "rules_fetches"
    __table_args__ = (
        Index("ix_rules_fetches_created_at", "created_at"),
        Index("ix_rules_fetches_account_id_created_at", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"))
    job_system: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
