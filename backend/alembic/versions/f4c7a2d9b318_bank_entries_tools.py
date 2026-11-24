"""bank entries: tools, a project's stack (KAN-738)

Revision ID: f4c7a2d9b318
Revises: c9e4a1d7b498
Create Date: 2026-11-09 21:10:00.000000

The tools a project names ("Next.js, TypeScript, FastAPI"), in the resume's
own spelling and order, which a built resume prints on its own line under
the project's heading. Only a project holds them (schemas/bank.py's
SECTION_FIELDS); empty for every row there now, as `coursework` is outside
Education. An upload read before this keeps its tools only as skills until
it is read again.

Apply it before the deploy that maps it: every entry INSERT names the
column, so deployed first, uploads, Import Again and Add answer 500. It only
adds a column with a default, so the running code never meets it and
applying it early is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4c7a2d9b318'
down_revision: Union[str, Sequence[str], None] = 'c9e4a1d7b498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_entries', sa.Column(
        'tools', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bank_entries', 'tools')
