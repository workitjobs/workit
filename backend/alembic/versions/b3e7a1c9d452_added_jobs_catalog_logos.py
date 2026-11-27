"""added_jobs_catalog_logos

Fills the logo sources of each job a student or Apply added (KAN-515,
KAN-542) from before add_job kept them: company_domain and company_logo_url
copied from a scraped posting (never another added job) of the same company (the whole name, case
aside) that has one, the domain first, as services/added_logos.py does for
a new added job. Only rows with neither source change, so a job with a logo
keeps it. Data only; the running code reads the columns as before, so
applying it early or late is safe. Downgrade changes nothing: which logos
were copied is not kept.

Revision ID: b3e7a1c9d452
Revises: 756dd185aedb
Create Date: 2026-11-26 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e7a1c9d452"
down_revision: str | Sequence[str] | None = "756dd185aedb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # One source per company name, picked in a single pass over the scraped
    # postings, then joined: never another added job, and no scan per row.
    op.execute(
        """
        UPDATE job_postings AS added
        SET company_domain = found.company_domain, company_logo_url = found.company_logo_url
        FROM (
            SELECT DISTINCT ON (lower(company_name))
                lower(company_name) AS name, company_domain, company_logo_url
            FROM job_postings
            WHERE company_id IS NULL AND NOT added_by_student AND company_name IS NOT NULL
              AND (company_domain IS NOT NULL OR company_logo_url IS NOT NULL)
            ORDER BY lower(company_name), company_domain IS NULL, company_logo_url IS NULL, id
        ) AS found
        WHERE lower(added.company_name) = found.name
          AND added.added_by_student AND added.company_id IS NULL
          AND added.company_domain IS NULL AND added.company_logo_url IS NULL
        """
    )


def downgrade() -> None:
    pass
