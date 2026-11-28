"""sent_applications

W11: what each application WorkIt Auto Apply filled sent, kept on WorkIt so
nothing of it stays on the student's Mac (models/applications.py,
Sent_Application), with each question's words once in form_questions
(Form_Question). Only new tables, which the code before it never reads,
so it goes on with b7e4c2a9d816 before the deploy: step 1 of KAN-834's
order is `upgrade d6a2f8c41e07` (backend/CLAUDE.md, Deployment). Apply it
only once it is on main, never from its branch (backend/alembic/CLAUDE.md).

Revision ID: d6a2f8c41e07
Revises: b7e4c2a9d816
Create Date: 2026-11-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd6a2f8c41e07'
down_revision: Union[str, Sequence[str], None] = 'b7e4c2a9d816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'form_questions',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('form_questions_text_key', 'form_questions', [sa.text('md5(text)')], unique=True)
    op.execute('ALTER TABLE public.form_questions ENABLE ROW LEVEL SECURITY')
    op.create_table(
        'sent_applications',
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("jsonb_typeof(answers) = 'array'", name='sent_applications_answers_array'),
        sa.ForeignKeyConstraint(['applicant_id', 'job_id'], ['job_applications.applicant_id', 'job_applications.job_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('applicant_id', 'job_id'),
    )
    # By hand: autogenerate never emits RLS (alembic/CLAUDE.md). ENABLE, never FORCE.
    op.execute('ALTER TABLE public.sent_applications ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('sent_applications')
    op.drop_index('form_questions_text_key', table_name='form_questions')
    op.drop_table('form_questions')
