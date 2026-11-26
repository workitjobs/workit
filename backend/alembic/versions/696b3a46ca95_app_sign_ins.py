"""app_sign_ins: WorkIt Auto Apply's one-time sign-in codes (KAN-723, W5)

Revision ID: 696b3a46ca95
Revises: e6a2c8f4b015
Create Date: 2026-11-15 12:00:00.000000

One row per sign-in of the desktop app: the sha256 of the one-time code the
website's /app-sign-in page asked for, the app's PKCE challenge, and when the
app traded the code for a session (app/services/app_sign_in.py). Rows live an
hour. A new table, so old code ignores it and it is safe to apply before or
after the deploy; until it is applied, the sign-in routes answer 500.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '696b3a46ca95'
down_revision: Union[str, Sequence[str], None] = 'e6a2c8f4b015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'app_sign_ins',
        sa.Column('code_hash', sa.Text(), nullable=False),
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column('challenge', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('traded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['applicant_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('code_hash'),
    )
    op.create_index(op.f('ix_app_sign_ins_applicant_id'), 'app_sign_ins', ['applicant_id'], unique=False)
    op.execute('ALTER TABLE public.app_sign_ins ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_app_sign_ins_applicant_id'), table_name='app_sign_ins')
    op.drop_table('app_sign_ins')
