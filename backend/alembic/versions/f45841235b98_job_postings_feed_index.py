"""job_postings_feed_idx: the feed's order over the listed jobs (KAN-916)

GET /jobs orders listed jobs by posted_at DESC NULLS LAST, then id. The only
listing index was on (status, created_at), so every page sorted all 41,000
listed jobs, and the Auto Apply Supported filter ran its regular expressions
on each before the sort (1.75 s for a page on 2026-11-18). With this partial
index a page walks the first rows of the index and stops.

The WHERE is services/postings.py's LISTED written out: Postgres uses a
partial index only for a query whose WHERE implies its predicate.

Only an index, so the deploy may land before or after it. Apply it only
once it is on main, never from its branch: a revision main lacks breaks
every teammate's Alembic (backend/alembic/CLAUDE.md). On the shared
database's 65,000 rows it builds in well under a second; writes to
job_postings wait for it meanwhile.

Revision ID: f45841235b98
Revises: c48811c7e5af
Create Date: 2026-11-18 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f45841235b98'
down_revision: Union[str, Sequence[str], None] = 'c48811c7e5af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "job_postings_feed_idx",
        "job_postings",
        [sa.text("posted_at DESC NULLS LAST"), "id"],
        postgresql_where=sa.text(
            "company_id IS NULL AND status = 'published' AND added_by_student IS false"
        ),
    )


def downgrade() -> None:
    op.drop_index("job_postings_feed_idx", table_name="job_postings")
