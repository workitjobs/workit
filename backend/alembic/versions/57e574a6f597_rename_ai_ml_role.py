"""rename ai ml role

Revision ID: 57e574a6f597
Revises: 36d339a2d6b4
Create Date: 2026-11-16 19:17:34.421092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57e574a6f597'
down_revision: Union[str, Sequence[str], None] = '36d339a2d6b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# "AI Machine Learning Engineer" wrapped onto two lines on onboarding's role
# tiles and was the longest name in the Role filter. "AI/ML Engineer" keeps
# "ML", so a student after Machine Learning Engineer roles still finds theirs.
# The slug never changes (ab07572bba38's rule): saved preferences, links
# (?role=ai_ml_engineer), job tags and the role resolver all name the slug,
# and the API reads this name for every role list (GET /jobs/facets), so this
# one row renames the role everywhere at once.
OLD = 'AI Machine Learning Engineer'
NEW = 'AI/ML Engineer'

_rename = sa.text("UPDATE job_roles SET name = :to WHERE slug = 'ai_ml_engineer' AND name = :from")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(_rename.bindparams(to=NEW, **{'from': OLD}))


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(_rename.bindparams(to=OLD, **{'from': NEW}))
