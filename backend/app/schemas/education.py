from pydantic import BaseModel


class EducationSuggestion(BaseModel):
    """One suggestion for the Education form: a school ("Stony Brook
    University", place "Stony Brook, NY") or a field of study (no place)."""

    name: str
    place: str | None = None
