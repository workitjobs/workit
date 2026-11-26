"""add description_attempts to job_sources

Revision ID: c5b587c8098e
Revises: 8bf848bb95e5
Create Date: 2026-11-17 23:17:36.948469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5b587c8098e'
down_revision: Union[str, Sequence[str], None] = '8bf848bb95e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_sources",
        sa.Column(
            "description_attempts",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("job_sources", "description_attempts")
