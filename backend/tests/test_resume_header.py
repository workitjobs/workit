"""The resume header read by rules and the profile it fills (KAN-436):
pure, no database. Every name, address and number here is made up."""

from app.services.header_fill import plan
from app.utils.resume_parser import HeaderReading, read_header

EMPTY = {}


def test_a_contact_line_with_a_location_and_a_second_line_of_text():
    header = read_header(
        "Jane Q. Doe\n"
        "Stony Brook, NY | (631) 555-0100 | jane.doe@example.com | linkedin.com/in/janedoe | github.com/janedoe\n"
        "Secret Clearance | Open to relocation\n"
        "Education\nStony Brook University  May 2027\n"
    )
    assert header == HeaderReading(
        email="jane.doe@example.com", phone="(631) 555-0100", location="Stony Brook, NY",
        linkedin="https://linkedin.com/in/janedoe", github="https://github.com/janedoe",
        text=("Secret Clearance", "Open to relocation"),
    )


def test_extra_links_a_street_and_us_citizen():
    # The street is never kept, only its city; "U.S. Citizen" is Application
    # Questions' answer, which the header prints itself
    header = read_header(
        "JOHN SMITH\n"
        "123 Main St, Albany, NY 12203 • john@example.org • +1 518-555-0123\n"
        "https://johnsmith.dev  www.behance.net/jsmith  U.S. Citizen\n"
        "Experience\n"
    )
    assert header.location == "Albany, NY"
    assert header.phone == "+1 518-555-0123"
    assert header.links == ("https://johnsmith.dev", "https://www.behance.net/jsmith")
    assert header.text == ()


def test_an_objective_sentence_above_the_first_heading_is_not_taken():
    header = read_header(
        "Alex Kim\n"
        "alex@example.com 6315550100 github.com/alexk\n"
        "Motivated computer science student seeking a summer internship to apply my skills in backend systems.\n"
        "Seeking a role.\n"
        "Experience\n"
    )
    assert header.text == ()
    assert (header.email, header.phone, header.github) == (
        "alex@example.com", "6315550100", "https://github.com/alexk")


def test_labels_come_off_and_an_abbreviation_is_no_sentence_end():
    header = read_header(
        "Priya Patel\n"
        "Email: priya@example.com   Phone: 212.555.0199   LinkedIn: linkedin.com/in/priya\n"
        "New York, NY · Authorized to work in the U.S. · Eligible for security clearance\n"
        "Skills\n"
    )
    assert header.location == "New York, NY"
    assert header.linkedin == "https://linkedin.com/in/priya"
    assert header.text == ("Authorized to work in the U.S.", "Eligible for security clearance")


def test_no_heading_near_the_top_means_no_header():
    assert read_header("Jane Doe\njane@example.com\n" + "words\n" * 20 + "Experience\n") == HeaderReading()
    assert read_header("") == HeaderReading()


# --- The profile it fills -------------------------------------------------

READ = HeaderReading(
    email="jane.doe@example.com", phone="(631) 555-0100", location="Stony Brook, NY",
    linkedin="https://linkedin.com/in/janedoe", github="https://github.com/janedoe",
    links=("https://janedoe.dev",), text=("Secret Clearance", "Open to relocation"),
)


def test_an_empty_profile_takes_every_field():
    fill = plan(EMPTY, READ, sign_in_email="jane@school.edu")
    assert fill.added == {
        "contact_email": "jane.doe@example.com", "phone_number": "(631) 555-0100",
        "location": "Stony Brook, NY", "linkedin_url": "https://linkedin.com/in/janedoe",
        "github_url": "https://github.com/janedoe", "portfolio_url": "https://janedoe.dev",
        "resume_header_extra": "Secret Clearance | Open to relocation",
    }
    assert fill.offers == [] and not fill.overflow


def test_a_value_is_never_overwritten_and_a_different_one_is_offered():
    profile = {
        "phone_number": "631-555-0100",  # the same number, written another way
        "location": "Albany, NY",
        "linkedin_url": "https://www.linkedin.com/in/janedoe/",  # the same link
        "resume_header_extra": "Open to relocation",
    }
    fill = plan(profile, READ, sign_in_email="jane.doe@example.com")
    assert "phone_number" not in fill.added and "linkedin_url" not in fill.added
    assert "contact_email" not in fill.added  # the sign-in email already says it
    assert "location" not in fill.added and "resume_header_extra" not in fill.added
    assert [(o.field, o.value) for o in fill.offers] == [
        ("location", "Stony Brook, NY"), ("resume_header_extra", "Secret Clearance | Open to relocation")]
    assert fill.added["github_url"] == "https://github.com/janedoe"


def test_a_link_with_no_free_field_joins_the_additional_line():
    profile = {"portfolio_url": "https://old.example.com", "other_url": "https://scholar.example.edu/x"}
    fill = plan(profile, HeaderReading(links=("https://janedoe.dev",), text=("Open to relocation",)))
    assert fill.added == {"resume_header_extra": "Open to relocation | janedoe.dev"}


def test_more_text_than_the_line_holds_is_left_for_the_header_panel():
    long = HeaderReading(text=("Active TS/SCI clearance with polygraph", "Open to relocation anywhere in the US",
                               "Available from June 2027"))
    fill = plan(EMPTY, long)
    assert fill.added == {} and fill.overflow


def test_a_value_my_profile_would_refuse_is_left_out():
    fill = plan(EMPTY, HeaderReading(phone="1" * 40, links=("https://bad host.com",)))
    assert fill.added == {} and fill.offers == []
