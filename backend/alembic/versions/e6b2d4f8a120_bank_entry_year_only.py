"""bank_entries.year_only: the dates given as a year alone (KAN-808)

Revision ID: e6b2d4f8a120
Revises: d8f3b6a1c947
Create Date: 2026-11-12 18:00:00.000000

A date is stored as the first day of its month, so "2019 – 2023" read from
an upload became January of each, and every resume printed "Jan. 2019 –
Jan. 2023". `year_only` lists which of the entry's dates (`start_month`,
`end_month`, `award_date`) name a year alone, so they print as the year.
A text[] defaulting to '{}', as `coursework` and `tools` are: every row
today gets the empty list, which prints as before. The CHECK keeps it to
those three names.

Apply it before the deploy: the model maps the column, so every read of a
bank entry answers 500 until it exists. Old code never reads it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e6b2d4f8a120'
down_revision: Union[str, Sequence[str], None] = 'd8f3b6a1c947'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_entries', sa.Column(
        'year_only', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False))
    op.create_check_constraint(
        'bank_entries_year_only_check', 'bank_entries',
        "year_only <@ ARRAY['start_month', 'end_month', 'award_date']::text[]",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('bank_entries_year_only_check', 'bank_entries', type_='check')
    op.drop_column('bank_entries', 'year_only')
