"""merge heads

Revision ID: 9755347bca9d
Revises: 696b3a46ca95, c3a7f2e5b148
Create Date: 2026-11-15 16:00:59.795588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9755347bca9d'
down_revision: Union[str, Sequence[str], None] = ('696b3a46ca95', 'c3a7f2e5b148')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
