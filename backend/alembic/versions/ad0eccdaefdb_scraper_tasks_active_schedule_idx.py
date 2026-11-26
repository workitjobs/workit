"""scraper_tasks_active_schedule_idx

Prevent two concurrent scrape_worker runs from creating duplicate tasks
for the same board.  The partial unique index guarantees at most one
pending-or-claimed task per schedule_id; create_tasks uses
ON CONFLICT DO NOTHING against it.

Revision ID: ad0eccdaefdb
Revises: a9d4c2e7f893
Create Date: 2026-11-24 00:52:15.000190

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ad0eccdaefdb'
down_revision: str | Sequence[str] | None = 'a9d4c2e7f893'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX scraper_tasks_active_schedule_idx"
        " ON scraper_tasks (schedule_id)"
        " WHERE status IN ('pending', 'claimed')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS scraper_tasks_active_schedule_idx")
