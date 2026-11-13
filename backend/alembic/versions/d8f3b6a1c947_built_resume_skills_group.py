"""built_resume_skills.group: a skill's group on one resume (KAN-586)

Revision ID: d8f3b6a1c947
Revises: c5e1a9d3b724
Create Date: 2026-11-11 15:00:00.000000

The editor's Sections outline moves a skill into another group on one
resume, and that resume alone: null is the bank's group (every row today),
"" no group, any other text that group. The bank's `bank_skills.group`
never changes here. A new nullable column, so old code ignores it and it is
safe to apply before the deploy; apply it before, or every resume read
answers 500 until it exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f3b6a1c947'
down_revision: Union[str, Sequence[str], None] = 'c5e1a9d3b724'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('built_resume_skills', sa.Column('group', sa.String(length=60), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('built_resume_skills', 'group')
