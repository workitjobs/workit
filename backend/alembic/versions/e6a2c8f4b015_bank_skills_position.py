"""bank_skills.position: the student's order of their skills (KAN-816)

Revision ID: e6a2c8f4b015
Revises: e6b2d4f8a120
Create Date: 2026-11-12 12:00:00.000000

The Experiences page's Skills dialog orders the groups and the skills in
each group, and the bank keeps that order: the bank lists skills by this
position, then by group and name as before, so a skill never placed (every
row today, and each one a reading adds) keeps today's order after the
placed ones. A new nullable column, so old code ignores it and it is safe to
apply before the deploy; apply it before, or every bank read, upload and
Add skill answers 500 until it exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a2c8f4b015'
down_revision: Union[str, Sequence[str], None] = 'e6b2d4f8a120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_skills', sa.Column('position', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bank_skills', 'position')
