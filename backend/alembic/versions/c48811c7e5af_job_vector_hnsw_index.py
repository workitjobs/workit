"""rank Best Match with an HNSW index on the job vectors (KAN-915)

Revision ID: c48811c7e5af
Revises: c5b587c8098e
Create Date: 2026-11-18 16:00:00.000000

An HNSW index over each job vector cast to halfvec(768), so score_jobs reads
a set's 500 nearest jobs from the index instead of every listed job's vector
from TOAST (45 s on the shared database, 2026-11-18). A halfvec expression,
not the vector column itself: half the size (72 MB for 41,489 jobs against
144 MB), so it fits in the shared database's 224 MB of shared buffers, and
the column keeps its type, so nothing that writes vectors changes
(app/services/matching/CLAUDE.md, "Candidates").

And a btree on updated_at, so the kept results' key (queries/jobs/kept.py,
made_from) reads the newest change from the index, not by scanning all
65,000 rows (24 ms warm, 0.5 to 2.8 s cold) on every Best Match request.

CONCURRENTLY, so the API and the import keep reading and writing
job_postings while they build, which is why they run outside the
migration's transaction. The HNSW build reads every vector once and holds
its graph in memory (at 64 MB it spills and takes twice as long), and the
shared database's statement_timeout (120 s) and maintenance_work_mem (32 MB)
are both below what it needs, so the session lifts them for the build.
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c48811c7e5af'
down_revision: Union[str, Sequence[str], None] = 'c5b587c8098e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXES = {
    "job_postings_embedding_hnsw_idx":
        "USING hnsw ((embedding::extensions.halfvec(768)) extensions.halfvec_cosine_ops)",
    "job_postings_updated_at_idx": "(updated_at)",
}


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        op.execute("SET maintenance_work_mem = '128MB'")
        for name, definition in INDEXES.items():
            # A build that failed or was cancelled leaves an INVALID index of
            # this name, which IF NOT EXISTS would keep and the planner never
            # uses.
            if not context.is_offline_mode():
                invalid = op.get_bind().execute(sa.text(
                    "SELECT 1 FROM pg_index WHERE NOT indisvalid"
                    f" AND indexrelid = to_regclass('public.{name}')"
                )).first()
                if invalid:
                    op.execute(f"DROP INDEX CONCURRENTLY public.{name}")
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON public.job_postings {definition}"
            )
        op.execute("RESET maintenance_work_mem")
        op.execute("RESET statement_timeout")


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        for name in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
