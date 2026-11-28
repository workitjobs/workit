"""resume_readings: the model that replied and its tokens (KAN-955)

Revision ID: 4c07869c8bf9
Revises: b3e7a1c9d452
Create Date: 2026-11-27 12:00:00.000000

The reading log (KAN-898) said a model read a resume, but not which one in
the chain or what the reply cost. Three columns, all nullable: `model` (the
chain's name for it), `input_tokens` and `output_tokens`. Null when no
model replied, and on every row written before this.

Apply it before the deploy that writes them: each upload, parse preview,
Import Updated Resume and Import Again adds a row with these columns, so
deployed first, each answers 500. Old code never names them, so applying
it early is safe.

No CHECK and no NOT NULL, as on the rest of the table: the row commits with
the student's upload, so a refused value would fail the upload. The writer
clips the name to the column's length.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c07869c8bf9'
down_revision: Union[str, Sequence[str], None] = 'b3e7a1c9d452'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('resume_readings', sa.Column('model', sa.String(length=100), nullable=True))
    op.add_column('resume_readings', sa.Column('input_tokens', sa.Integer(), nullable=True))
    op.add_column('resume_readings', sa.Column('output_tokens', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('resume_readings', 'output_tokens')
    op.drop_column('resume_readings', 'input_tokens')
    op.drop_column('resume_readings', 'model')
