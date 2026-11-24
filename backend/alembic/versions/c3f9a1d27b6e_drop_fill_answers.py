"""applicant profiles: drop fill_answers

W11's step 5 (docs/desktop_application_auto_apply.md): what Apply's sync
(KAN-746, gone) kept for each student. The Answer bank (answer_banks) holds
it now, and no code maps the column.

Apply it only AFTER the deploy that stopped mapping the column: the code
before it selects fill_answers with every profile read, so dropped first,
every signed-in request answers 500 (backend/CLAUDE.md, Deployment).

Revision ID: c3f9a1d27b6e
Revises: b7e4c2a9d816
Create Date: 2026-11-24 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3f9a1d27b6e'
down_revision: Union[str, Sequence[str], None] = 'b7e4c2a9d816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('applicant_profiles_fill_answers_object', 'applicant_profiles', type_='check')
    op.drop_column('applicant_profiles', 'fill_answers')


def downgrade() -> None:
    """Downgrade schema: the column as 7f07adcaef4e made it, empty."""
    op.add_column('applicant_profiles', sa.Column(
        'fill_answers', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False,
    ))
    op.create_check_constraint(
        'applicant_profiles_fill_answers_object', 'applicant_profiles', "jsonb_typeof(fill_answers) = 'object'",
    )
