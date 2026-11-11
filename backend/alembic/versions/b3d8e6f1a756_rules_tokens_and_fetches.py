"""rules_tokens and rules_fetches: the Rules table's site tokens and fetch log (KAN-756)

Revision ID: b3d8e6f1a756
Revises: f4c7a2d9b318
Create Date: 2026-11-10 19:00:00.000000

rules_tokens holds the sha256 of each site token (one account, one job
system, a few minutes), and rules_fetches one row per fetch of a job
system's Rules table (account, job system, time) for anomaly review. Both
go with the account. New tables, so old code ignores them and they are safe
to apply before the deploy; apply them before it, or /extension/rules
answers 500 until they exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d8e6f1a756'
down_revision: Union[str, Sequence[str], None] = 'f4c7a2d9b318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'rules_tokens',
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('job_system', sa.String(length=24), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token_hash'),
    )
    op.create_index('ix_rules_tokens_created_at', 'rules_tokens', ['created_at'])
    op.execute('ALTER TABLE public.rules_tokens ENABLE ROW LEVEL SECURITY')
    op.create_table(
        'rules_fetches',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('job_system', sa.String(length=24), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rules_fetches_created_at', 'rules_fetches', ['created_at'])
    op.create_index('ix_rules_fetches_account_id_created_at', 'rules_fetches', ['account_id', 'created_at'])
    op.execute('ALTER TABLE public.rules_fetches ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('rules_fetches')
    op.drop_table('rules_tokens')
