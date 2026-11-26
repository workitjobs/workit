"""scraper_cycle_leases

One-row table for the scraper cycle lease (D5). Only one worker process can
run a cycle at a time: take_lease does UPDATE ... WHERE expires_at < now()
RETURNING, and a second process that cannot take the lease exits.

Seeded with one row whose expires_at is epoch, so the first cycle can take it
without an INSERT race.

Apply before the code that maps this table deploys: the model names every
column, so every query fails on a database without them. It only adds a table,
so the running code never meets it and applying early is safe.

Revision ID: 756dd185aedb
Revises: ad0eccdaefdb
Create Date: 2026-11-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "756dd185aedb"
down_revision: str | Sequence[str] | None = "ad0eccdaefdb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scraper_cycle_leases",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("holder", sa.Text()),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "ALTER TABLE public.scraper_cycle_leases ENABLE ROW LEVEL SECURITY"
    )
    # Seed one row with expires_at at epoch so the first cycle can take it.
    op.execute(
        "INSERT INTO scraper_cycle_leases (expires_at)"
        " VALUES ('1970-01-01 00:00:00+00')"
    )


def downgrade() -> None:
    op.drop_table("scraper_cycle_leases")
