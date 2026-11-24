"""
One student as the WorkIt extension assembles them for the Fill engine
(autofiller_extension/src/background/api.js, `fetchAutofillProfile`), read
here from the same rows its routes answer: the profile row, the experience
bank as `GET .../bank` answers it, the Application answers, the job
preferences' visa (which fills two unanswered work questions, as the
extension does) and the names of the default resume and the transcript.
`services/engine_profile.py` maps it to the engine's profile for WorkIt
Auto Apply (`GET /apply-app/profile`, W11). Each value is its JSON, as the
extension receives it, so the two map the same input.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.built_resume import Built_Resume
from app.models.documents import Student_Document
from app.models.profiles import Applicant_Profile
from app.models.resume import Resume
from app.queries.autofill_answers import fetch_bank
from app.queries.preferences import fetch_preferences
from app.schemas.autofill_answers import answers_from_bank
from app.services.bank import bank_response, load_bank, load_holdings


async def engine_student(db: AsyncSession, applicant_id: uuid.UUID, account_email: str, full_name: str) -> dict | None:
    """The student, or None with no profile. `files` names where WorkIt Auto Apply reads each file's bytes."""
    profile = await db.get(Applicant_Profile, applicant_id)
    if profile is None:
        return None
    bank = bank_response(await load_bank(db, applicant_id), await load_holdings(db, applicant_id)).model_dump(mode="json")
    answers = answers_from_bank(await fetch_bank(db, applicant_id)).model_dump(mode="json")
    visa = getattr(await fetch_preferences(db, applicant_id), "visa", None)
    # A real saved answer always wins; the job search's visa filter answers only these two while they're unanswered.
    if answers.get("work_authorized_us") is None:
        answers["work_authorized_us"] = "yes" if visa is None else None
    if answers.get("needs_sponsorship") is None:
        answers["needs_sponsorship"] = "yes" if visa == "sponsors" else "no" if visa is None else None
    resume, files = None, {}
    if profile.default_resume_id and (upload := await db.get(Resume, profile.default_resume_id)):
        ext = (upload.original_filename or "").rsplit(".", 1)[-1].lower() if upload.original_filename else "pdf"
        resume = {"filename": upload.original_filename or f"resume.{ext}"}
        files["resume"] = {"name": resume["filename"], "uploaded_resume_id": str(upload.id)}
    elif profile.default_built_resume_id and (built := await db.get(Built_Resume, profile.default_built_resume_id)):
        resume = {"filename": f"{built.name or 'Resume'}.pdf"}
        files["resume"] = {"name": resume["filename"], "built_resume_id": str(built.id)}
    transcript = None
    if document := await db.get(Student_Document, (applicant_id, "transcript")):
        ext = (document.original_filename or "").rsplit(".", 1)[-1].lower() or "pdf"
        name = document.original_filename or f"transcript.{ext}"
        transcript = {"filename": f"Transcript_{name}" if resume and name == resume["filename"] else name}
        files["transcript"] = {"name": transcript["filename"]}
    return {
        "email": profile.contact_email or account_email,
        "full_name": full_name,
        "first_name": profile.first_name,
        "middle_name": profile.middle_name,
        "last_name": profile.last_name,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "github_url": profile.github_url,
        "other_url": profile.other_url,
        "bank": bank if bank["entries"] else None,
        "answers": answers,
        "resume": resume,
        "transcript": transcript,
        "fill": {"profile": profile.fill_profile or {}, "policies": profile.fill_policies or {}},
        "files": files,
    }
