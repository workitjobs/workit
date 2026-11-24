"""answer_banks

W11 (docs/desktop_application_auto_apply.md): one Answer bank row for each
student, which WorkIt Auto Apply and the extension read whole and the
student edits in the app (models/CLAUDE.md, "The Answer bank").

Apply it right after the merge, before the deploy is live: the deployed
code reads answer_banks on every Plan (GET .../answer-bank answers 500
without it).
The table starts empty: a student's first read fills their row from
applicant_profiles.fill_answers and their saved answers
(app/auto_apply/answer_bank.py), so nothing is run by hand. Apply it only
once it is on main, never from its branch (backend/alembic/CLAUDE.md).

Revision ID: b7e4c2a9d816
Revises: a9d4c2e7f893
Create Date: 2026-11-18 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7e4c2a9d816'
down_revision: Union[str, Sequence[str], None] = 'a9d4c2e7f893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'answer_banks',
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column(
            'answers', postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("jsonb_typeof(answers) = 'object'", name='answer_banks_answers_object'),
        sa.ForeignKeyConstraint(['applicant_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('applicant_id'),
    )
    # By hand: autogenerate never emits RLS (alembic/CLAUDE.md). ENABLE, never FORCE.
    op.execute('ALTER TABLE public.answer_banks ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('answer_banks')
