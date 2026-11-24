"""merge description refresh and Qwen3 migration heads

Revision ID: 06edf44926a1
Revises: b27f4b974d5c, e8c3f1a7b925
Create Date: 2026-11-08 16:25:04.196642

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "06edf44926a1"
down_revision: Union[str, Sequence[str], None] = ("b27f4b974d5c", "e8c3f1a7b925")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join histories; each parent retains its own schema/data changes."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
