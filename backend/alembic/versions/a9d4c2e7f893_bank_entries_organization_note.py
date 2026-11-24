"""bank entries: organization_note, a description of the organization (KAN-893)

Revision ID: a9d4c2e7f893
Revises: e4bac6ea0c32
Create Date: 2026-11-16 12:00:00.000000

Chained after KAN-892's `e4bac6ea0c32` (a project's link on its title): both
were written on `36d339a2d6b4` in parallel, and two heads fail `upgrade head`.

A description the resume writes in brackets after an organization's name
("Series A Fintech Startup" in "Lakeside Labs (Series A Fintech Startup)"),
kept apart from the name so every form, Apply and the tracker get the name
alone. A built resume still prints the two together, as the resume did.
Null for every row there now: an upload read before this keeps the
description in its organization until it is read again.

Apply it before the deploy that maps it: every entry INSERT names the
column, so deployed first, uploads, Import Again and Add answer 500, and
every bank read selects it. It only adds a nullable column, so the running
code never meets it and applying it early is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9d4c2e7f893'
down_revision: Union[str, Sequence[str], None] = 'e4bac6ea0c32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_entries', sa.Column('organization_note', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bank_entries', 'organization_note')
