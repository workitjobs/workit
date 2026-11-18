"""custom roles on preferences

Revision ID: 8bf848bb95e5
Revises: 57e574a6f597
Create Date: 2026-11-16 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8bf848bb95e5'
down_revision: Union[str, Sequence[str], None] = '57e574a6f597'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Roles a student typed that job_roles lacks ("UX Researcher"), kept with
# their saved preferences so the Jobs page keeps finding them by title. Text,
# not applicant_job_roles rows: those carry a foreign key to job_roles, and a
# custom role has no row there. NOT NULL with '{}' like the other picks, so
# no pick is an empty list. The cap is schemas/jobs.py's MAX_CUSTOM_ROLES.
#
# Only adds a column with a default and a CHECK every row meets, so it is
# safe before the deploy; deployed first, the model selects the column on
# every preferences read and write, and onboarding's Find Jobs, Settings' Job
# Preferences and the Jobs page's first visit answer 500.


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'applicant_preferences',
        sa.Column(
            'custom_roles',
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'applicant_preferences_custom_roles_cap',
        'applicant_preferences',
        'cardinality(custom_roles) <= 5',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'applicant_preferences_custom_roles_cap', 'applicant_preferences', type_='check'
    )
    op.drop_column('applicant_preferences', 'custom_roles')
