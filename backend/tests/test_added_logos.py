"""Where an added job's logo comes from (app/services/added_logos.py): the
employer's own site gives its domain, a vendor's host gives none."""

import pytest

from app.services.added_logos import own_site


@pytest.mark.parametrize(
    ("url", "domain"),
    [
        ("https://careers.airbnb.com/positions/123?gh_jid=123", "airbnb.com"),
        ("https://jobs.intel.co.uk/roles/1", "intel.co.uk"),
        ("https://job-boards.greenhouse.io/twitch/jobs/1", None),
        ("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/1", None),
        ("https://www.linkedin.com/jobs/view/1", None),
        ("https://acme.bamboohr.com/careers/1", None),
        ("https://acme.github.io/careers", None),
        ("https://airtable.com/shrAbc", None),
        ("not a link", None),
        ("https://localhost/jobs", None),
        ("http://10.0.0.1/jobs", None),
    ],
)
def test_own_site_is_the_employers_registered_domain_never_a_vendors(url, domain):
    found = own_site(url)
    assert (found[0] if found else None) == domain
    if found:
        assert domain in found[1]
