"""applicant_profiles.resume_header_extra: the resume header's Additional line (KAN-436)

Revision ID: c5e1a9d3b724
Revises: b3d8e6f1a756
Create Date: 2026-11-11 12:00:00.000000

One short line of the student's own text under the header's contact line
("Secret clearance | Open to relocation"), shared by every resume as the
other header fields are; each resume can hide it. A new nullable column, so
old code ignores it and it is safe to apply before the deploy; apply it
before, or the profile and the editor answer 500 until it exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e1a9d3b724'
down_revision: Union[str, Sequence[str], None] = 'b3d8e6f1a756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('applicant_profiles', sa.Column('resume_header_extra', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applicant_profiles', 'resume_header_extra')
