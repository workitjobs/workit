"""model_usage: WorkIt Auto Apply's daily model use per student (KAN-723)

Revision ID: 3132c5026bf6
Revises: d8f3b6a1c947
Create Date: 2026-11-13 12:00:00.000000

One row per student and day (UTC): the tokens their Model route
calls spent, for the Usage cap, and their calls in the current minute
(app/queries/model_usage.py). A new table, so old code ignores it and it is
safe to apply before or after the deploy; until it is applied, the Model
route answers 500.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3132c5026bf6'
down_revision: Union[str, Sequence[str], None] = 'd8f3b6a1c947'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'model_usage',
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('input_tokens', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('output_tokens', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('calls', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('minute', sa.DateTime(timezone=True), nullable=False),
        sa.Column('minute_calls', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['applicant_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('applicant_id', 'day'),
    )
    op.execute('ALTER TABLE public.model_usage ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('model_usage')
