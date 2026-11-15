"""merge app_sign_ins and scraper fingerprint heads (KAN-837)

Revision ID: 076111eab7cb
Revises: 696b3a46ca95, c3a7f2e5b148
Create Date: 2026-11-15 15:57:16.775251

KAN-723's app_sign_ins (696b3a46ca95) and KAN-722's scraper fingerprint
columns (c3a7f2e5b148) were each moved onto e6a2c8f4b015 and merged, so main
had two heads and `alembic upgrade head`, the backend tests' included,
failed with "Multiple head revisions". This revision only joins them: no
schema change, and a database that applied either one upgrades through the
other (alembic/CLAUDE.md: never re-parent a migration that may be applied).
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '076111eab7cb'
down_revision: Union[str, Sequence[str], None] = ('696b3a46ca95', 'c3a7f2e5b148')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
