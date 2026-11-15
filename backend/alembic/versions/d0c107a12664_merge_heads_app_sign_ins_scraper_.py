"""merge heads: app_sign_ins + scraper_fingerprint

Revision ID: d0c107a12664
Revises: 696b3a46ca95, c3a7f2e5b148
Create Date: 2026-11-15 16:06:49.869822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0c107a12664'
down_revision: Union[str, Sequence[str], None] = ('696b3a46ca95', 'c3a7f2e5b148')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
