"""job_postings repost column

Revision ID: a1b2c3d4e5f6
Revises: d8f3b6a1c947
Create Date: 2026-11-14

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "d8f3b6a1c947"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_postings",
        sa.Column("repost", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("job_postings", "repost")
