"""Quiet board stagger and fingerprint rest for the scraper worker (KAN-722).

Four columns on scraper_schedules: fingerprint (8-char hex CRC32 of the
board's kept postings), unchanged_reads (how many consecutive reads matched),
fingerprint_until (when the board may be read again) and has_kept (sticky:
True once the board has produced a kept posting).

All nullable or defaulted, so applying early is safe; the running code never
meets them.

Revision ID: c3a7f2e5b148
Revises: e6a2c8f4b015
Create Date: 2026-11-14 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7f2e5b148"
down_revision: str | Sequence[str] | None = "e6a2c8f4b015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scraper_schedules",
        sa.Column("fingerprint", sa.Text(), nullable=True),
    )
    op.add_column(
        "scraper_schedules",
        sa.Column(
            "unchanged_reads",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "scraper_schedules",
        sa.Column(
            "fingerprint_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "scraper_schedules",
        sa.Column(
            "has_kept",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("scraper_schedules", "has_kept")
    op.drop_column("scraper_schedules", "fingerprint_until")
    op.drop_column("scraper_schedules", "unchanged_reads")
    op.drop_column("scraper_schedules", "fingerprint")
