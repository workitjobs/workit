"""bank entries: link_on_title, a project's link on its title (KAN-892)

Revision ID: e4bac6ea0c32
Revises: d0f6c68dae1d
Create Date: 2026-11-16 12:00:00.000000

Chained after KAN-891's `d0f6c68dae1d` (minors and concentration): both
were written on `36d339a2d6b4` in parallel, and two heads fail `upgrade head`.

Whether a project's resume line makes its title the link, in place of
printing the address after the bar ("Budget Buddy | github.com/jr/budget").
Only a project holds it (schemas/bank.py's SECTION_FIELDS); false for every
row there now, so every resume prints as before. A reading turns it on for
a project the resume names by its address ("budgetbuddy.app | Personal
Finance Tracker"), which also gets that address as its link.

Apply it before the deploy that maps it: every entry INSERT names the
column, so deployed first, uploads, Import Again and Add answer 500. It only
adds a column with a default, so the running code never meets it and
applying it early is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4bac6ea0c32'
down_revision: Union[str, Sequence[str], None] = 'd0f6c68dae1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_entries', sa.Column(
        'link_on_title', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bank_entries', 'link_on_title')
