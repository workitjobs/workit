"""Clear every job and bank vector for the move to Qwen3 embeddings (KAN-726)

Data only, no schema change. Vectors from two models cannot be compared,
even at one width, and nothing records which model made a stored vector
(services/matching/CLAUDE.md, "One model, everywhere"). So before the team
computer writes Qwen3 vectors (`qwen3-embedding:4b`, cut to 768 values),
every vector already stored goes: Nomic ones from laptops and Gemini ones
from the job alerts. The columns stay vector(768).

Apply it after the deploy that makes `none` the default provider, so no
other machine writes old-model vectors again, and before starting the bank
job on the team computer (docs/scraper_gh_action/plan.md, The cutover).
Applied before that deploy, the old API or the job alerts could write
Gemini vectors back in between.

Its downgrade does nothing: the cleared vectors cannot be brought back, and
the bank job and the import remake them.

Revision ID: e8c3f1a7b925
Revises: b2c3d4e5f6a7
Create Date: 2026-11-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e8c3f1a7b925'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # updated_at is left alone on both: Home's kept matches are keyed on it,
    # and a bank with no vector is stale by its embedding alone.
    op.execute("UPDATE job_postings SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute(
        "UPDATE experience_banks SET embedding = NULL, embedded_at = NULL"
        " WHERE embedding IS NOT NULL OR embedded_at IS NOT NULL"
    )


def downgrade() -> None:
    pass
