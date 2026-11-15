"""Send report's shapes (D26, KAN-837, routers/apply_reports.py): the support form a student fills in WorkIt Auto
Apply's window (a category, their own words, whether WorkIt may email them), and, when they include one, an
Application's Record and masked Trace, as the app sends them (apply-agent/src/apply/report.py)."""

import base64
import binascii
import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BODY_MAX = 24_000_000  # bytes of a report's JSON: every part at its cap, the screenshots in base64
TEXT_MAX = 1_000_000  # characters of one of the Record's text files (page.html is the largest)
TRACE_MAX = 4_000_000  # characters of the Trace; the app keeps its end, where a failure is
PNG_MAX = 4_000_000  # bytes of one screenshot

TextFile = Literal["answers.json", "essays.md", "verification.json", "asks.json", "page.html"]
# What the report is about, as the form offers it (apply.report.CATEGORIES has the words the window shows).
Category = Literal["form", "answer", "sign_in", "app", "other"]
Screenshot = Literal["form.png", "after-submit.png"]
PNG = b"\x89PNG\r\n\x1a\n"


class ApplyReportRequest(BaseModel):
    """What the app sends: the form's category, the student's own words and whether WorkIt may email them, and, for
    a report about one Application, the Application as its Tracker row names it, the Record's files and the masked
    Trace. A general question names no Application and carries none of them. Nothing outside these fields is
    taken."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    # What happened, in the student's own words: the one part every report has.
    note: str = Field(min_length=1, max_length=2000)
    contact_ok: bool = False
    application_id: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=300)
    role: str = Field(default="", max_length=300)
    posting_url: str = Field(default="", max_length=2000)
    outcome: str = Field(default="", max_length=40)
    files: dict[TextFile, Annotated[str, Field(max_length=TEXT_MAX)]] = Field(default_factory=dict)
    # Each screenshot in base64; checked to be a PNG of at most PNG_MAX bytes.
    screenshots: dict[Screenshot, str] = Field(default_factory=dict)
    trace: str = Field(default="", max_length=TRACE_MAX)

    @field_validator("posting_url")
    @classmethod
    def _a_web_link(cls, value: str) -> str:
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("posting_url is an http or https link")
        return value

    @field_validator("screenshots")
    @classmethod
    def _pngs(cls, value: dict[str, str]) -> dict[str, str]:
        for name, encoded in value.items():
            try:
                png = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                raise ValueError(f"{name} is not base64") from None
            if not png.startswith(PNG) or len(png) > PNG_MAX:
                raise ValueError(f"{name} is not a PNG of at most {PNG_MAX} bytes")
        return value

    def png(self, name: Screenshot) -> bytes | None:
        return base64.b64decode(self.screenshots[name]) if name in self.screenshots else None


class ApplyReportStored(BaseModel):
    id: str


class ApplyReportSummary(BaseModel):
    id: str
    created_at: datetime.datetime
    applicant_id: str
    # The account's email, for the team's reply when contact_ok is true.
    email: str
    category: str
    contact_ok: bool
    application_id: str
    company: str
    role: str
    posting_url: str
    outcome: str
    note: str


class ApplyReportList(BaseModel):
    reports: list[ApplyReportSummary]
    total: int


class ApplyReportDetail(ApplyReportSummary):
    files: dict[str, str]
    # The screenshots it has, each read with GET /admin/apply-reports/{id}/screenshots/{name}.
    screenshots: list[str]
    trace: str
