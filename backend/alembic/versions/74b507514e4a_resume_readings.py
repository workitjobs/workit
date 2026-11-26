"""resume_readings: a log of each reading of an upload (KAN-898)

Revision ID: 74b507514e4a
Revises: f45841235b98
Create Date: 2026-11-16 12:00:00.000000

One row per reading of an uploaded resume: the account, the route (upload,
preview, update, import_again), the reader (model or parser), why the
parser's reading was saved, how long it took, how many entries and skills
it found and how many of the model's fields the check against the text
dropped (app/models/resume_readings.py). Never the resume's text, a name
or a field's value. Kept 90 days (services/retention.py). The text columns
have no CHECK on purpose: the row commits with the upload, so a refused
value would fail the student's upload.

A new table, so old code ignores it and it is safe to apply before the
deploy. Deployed first, every upload, preview, Import Updated Resume and
Import Again answers 500, since each writes a row.

Written on `36d339a2d6b4` and moved onto `f45841235b98` (KAN-916), main's
newest, when main was merged in: two heads fail `upgrade head`. It was
applied nowhere shared before the move.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74b507514e4a'
down_revision: Union[str, Sequence[str], None] = 'f45841235b98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'resume_readings',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('applicant_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('route', sa.String(length=16), nullable=False),
        sa.Column('read_by', sa.String(length=8), nullable=False),
        sa.Column('reason', sa.String(length=24), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('entries', sa.Integer(), nullable=False),
        sa.Column('skills', sa.Integer(), nullable=False),
        sa.Column('fields_dropped', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['applicant_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resume_readings_created_at', 'resume_readings', ['created_at'])
    op.create_index('ix_resume_readings_applicant_id', 'resume_readings', ['applicant_id'])
    op.execute('ALTER TABLE public.resume_readings ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resume_readings')
