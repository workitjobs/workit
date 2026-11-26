"""apply_reports: WorkIt Auto Apply's Send report (KAN-837)

Revision ID: 36d339a2d6b4
Revises: 076111eab7cb
Create Date: 2026-11-15 16:01:39.372467

One row per report a student sent from WorkIt Auto Apply's support form
(D26): its category, their words and whether WorkIt may email them, and,
when they included one Application, its Record and masked Trace
(app/models/apply_reports.py). No retention period: the team deletes a
report once its problem is fixed (DELETE /admin/apply-reports/{id}). A new
table, so old code ignores it and it is safe to apply before or after the
deploy; until it is applied, POST /apply-app/reports answers 500.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '36d339a2d6b4'
down_revision: Union[str, Sequence[str], None] = '076111eab7cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'apply_reports',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=16), nullable=False),
        sa.Column('contact_ok', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('application_id', sa.String(length=200), server_default='', nullable=False),
        sa.Column('company', sa.Text(), server_default='', nullable=False),
        sa.Column('role', sa.Text(), server_default='', nullable=False),
        sa.Column('posting_url', sa.Text(), server_default='', nullable=False),
        sa.Column('outcome', sa.String(length=40), server_default='', nullable=False),
        sa.Column('note', sa.Text(), server_default='', nullable=False),
        sa.Column('files', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('form_png', sa.LargeBinary(), nullable=True),
        sa.Column('after_submit_png', sa.LargeBinary(), nullable=True),
        sa.Column('trace', sa.Text(), server_default='', nullable=False),
        sa.ForeignKeyConstraint(['applicant_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_apply_reports_applicant_id', 'apply_reports', ['applicant_id'])
    op.create_index('ix_apply_reports_created_at', 'apply_reports', [sa.text('created_at DESC')])
    op.create_check_constraint(
        'apply_reports_category_check', 'apply_reports', "category IN ('form', 'answer', 'sign_in', 'app', 'other')")
    op.execute('ALTER TABLE public.apply_reports ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('apply_reports')
