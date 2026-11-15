"""The experience bank's API (KAN-206): one student's entries, bullets and
skills. Every route checks the token's account owns `applicant_id` first;
a row of another applicant answers 404. The rules (embedding clearing, the
duplicate check, bullet order) live in `app/services/bank.py`.

Months are "YYYY-MM". An entry's `end_kind` is "month", "present" or
"expected"; present has no `end_month`, the others need one. Section fields
(Education: degree, field_of_study, gpa, gpa_scale, coursework, honors;
Projects: link, tools; Certifications: issuer; Awards: award_date) must be empty on
entries of other sections, or the request answers 422.

GET    /applicants/{id}/bank                     -> BankResponse
POST   /applicants/{id}/bank/entries             EntryCreate -> 201 EntryResponse
       ?resume_id= saves it into the resume the Experiences view shows: an
       upload owns it (ADR 0005); a built resume shows it, at the end of its
       section. Without one, it is the student's own. 404 for a resume that
       is not the applicant's.
       409 {detail, duplicate: EntryResponse} when section, title and
       organization match an entry of the same owner, ignoring case;
       ?allow_duplicate=true saves it anyway ("Save as new").
PATCH  /applicants/{id}/bank/entries/{entry_id}  EntryUpdate -> EntryResponse
DELETE /applicants/{id}/bank/entries/{entry_id}  -> 204 (its bullets too)
POST   /applicants/{id}/bank/entries/delete      DeleteMany -> 204
       Clear All (KAN-352): the entries a section shows, all or none. One
       id that is not the applicant's answers 404 and deletes nothing.
GET    /applicants/{id}/bank/entries/{entry_id}/resumes -> {"built_resumes": n}
       how many built resumes show the entry, for the delete confirm (story 18)
POST   /applicants/{id}/bank/entries/{entry_id}/bullets  BulletCreate -> 201 BulletResponse (appended)
PATCH  /applicants/{id}/bank/bullets/{bullet_id} BulletUpdate -> BulletResponse
DELETE /applicants/{id}/bank/bullets/{bullet_id} -> 204
POST   /applicants/{id}/bank/skills              SkillCreate -> 201 SkillResponse
       ?resume_id= as for entries; 409 if the owner has the name already
PATCH  /applicants/{id}/bank/skills/{skill_id}   SkillUpdate -> SkillResponse (409 if the name exists)
DELETE /applicants/{id}/bank/skills/{skill_id}   -> 204
POST   /applicants/{id}/bank/skills/delete       DeleteMany -> 204, as entries/delete
       A deleted skill is remembered as removed (KAN-369): no reading or
       Tailor adds it again until the student adds it here by hand.
POST   /applicants/{id}/bank/sections            CustomSectionCreate -> 201 CustomSectionResponse
       A section the student names (KAN-498): `layout` "entries" or
       "lines". ?resume_id= as for entries (an upload owns it; under a built
       resume it is the student's own). 409 at MAX_CUSTOM_SECTIONS for the
       owner, or when it has the name already, ignoring case. 422 for a
       fixed section's name. Its entries are POST /entries with section
       "custom" and its `custom_section_id`.
PATCH  /applicants/{id}/bank/sections/{section_id} CustomSectionUpdate -> CustomSectionResponse (409 as above)
DELETE /applicants/{id}/bank/sections/{section_id} -> 204 (its entries too)
POST   /applicants/{id}/bank/import              ImportRequest -> ImportResponse
       Import Again: reads one uploaded resume's stored text (resume_id,
       else the default resume, else the newest) as every upload is read
       (`services/resume_reading.py`: the model first while the student has
       an AI reading left today, the heuristic parser behind it; KAN-732,
       ADR 0007) and writes it into the bank with `import_upload`, as upload
       does: the reading replaces the entries and skills the upload owns
       (ADR 0005). Answers what it wrote (`entries_added`, `skills_added`),
       who read it (`read_by`, "model" or "parser") and `uses_left`. A model
       reading counts one parsing use (cap 1, 10% of the pool), committed
       with the bank writes; a failed or refused model reading falls back to
       the parser and counts none. A resume nothing can read leaves the
       upload with nothing; no uploaded resume (or another student's)
       answers 404.

GET /bank also sends `resumes` (every uploaded, base and tailored resume,
with `kind`, `name`, a tailored one's `posting`, the starred one's
`primary` and `edited_at`, the resume table's date) and, on each entry
and skill, `resume_ids`: the upload that owns it, if any, then the built
resumes that show it (KAN-343, ADR 0005). Each entry's `copy_group` is shared
by the entries that are copies of one (`copy_key`, KAN-440).
"""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM

from app.db import get_session, get_supabase
from app.deps import get_current_account, owned_applicant
from app.models.resume import Resume
from app.queries.bank import owned_upload_id
from app.schemas.auth import AuthenticatedAccount
from app.schemas.bank import (
    BankResponse,
    BulletCreate,
    BulletResponse,
    BulletUpdate,
    CustomSectionCreate,
    CustomSectionResponse,
    CustomSectionUpdate,
    DeleteMany,
    DuplicateEntry,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    ImportRequest,
    ImportResponse,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.services import bank as service
from app.services import built_resumes, header_fill, stored_files
from app.services.bank import bank_response, entry_response
from app.services.models import get_llm
from app.services.resume_reading import read_upload
from app.services.text_extraction import extract

router = APIRouter(prefix="/applicants/{applicant_id}/bank", tags=["bank"])
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _writing(session: AsyncSession) -> AsyncIterator[None]:
    """Commit on success; turn the service's errors into HTTP answers."""
    try:
        yield
        await session.commit()
    except service.NotFound:
        await session.rollback()
        raise HTTPException(404, "Not found in your experience bank")
    except service.DuplicateSkillError:
        await session.rollback()
        raise HTTPException(409, "That skill is already in your experience bank")
    except service.SectionError as exc:
        await session.rollback()
        raise HTTPException(409, str(exc))
    except ValidationError as exc:
        await session.rollback()
        raise RequestValidationError(exc.errors(include_url=False, include_context=False))
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(500, "Failed to save your experience bank")


@router.get("", response_model=BankResponse)
async def get_bank(
    applicant_id: uuid.UUID = Depends(owned_applicant),
    built_resume_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> BankResponse:
    """The bank, with `built_resume_id`'s own skills too when given (the
    editor of that resume names them). The skills are the applicant's own
    rows, so an id that is not theirs adds nothing."""
    bank = await service.load_bank(session, applicant_id, local_to=[built_resume_id] if built_resume_id else [])
    return bank_response(bank, await service.load_holdings(session, applicant_id))


async def _target(
    session: AsyncSession, applicant_id: uuid.UUID, resume_id: uuid.UUID | None
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Where an Add under a resume pick goes: (the upload that will own the
    item, the built resume that will show it), at most one of them. Raises
    NotFound for a resume that is not the applicant's."""
    if resume_id is None:
        return None, None
    upload = await owned_upload_id(session, applicant_id, resume_id)
    if upload is not None:
        return upload, None
    await built_resumes.get_resume(session, applicant_id, resume_id)
    return None, resume_id


@router.post(
    "/entries",
    status_code=201,
    response_model=EntryResponse,
    responses={409: {"model": DuplicateEntry}},
)
async def create_entry(
    body: EntryCreate,
    allow_duplicate: bool = False,
    resume_id: uuid.UUID | None = None,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
):
    try:
        async with _writing(session):
            owner, built = await _target(session, applicant_id, resume_id)
            entry = await service.create_entry(
                session, applicant_id, body, body.bullets, resume_id=owner, allow_duplicate=allow_duplicate
            )
            if built is not None:
                await built_resumes.update_choices(
                    session, applicant_id, built, entries=[{"entry_id": entry.row.id, "shown": True}]
                )
    except service.DuplicateEntryError as exc:
        # Built before the rollback, which expires the loaded rows.
        payload = DuplicateEntry(detail=str(exc), duplicate=entry_response(exc.existing))
        await session.rollback()
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))
    # The pick holds it now, so the page shows it there at once.
    return entry_response(entry, [i for i in (owner, built) if i is not None])


@router.patch("/entries/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    body: EntryUpdate,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> EntryResponse:
    async with _writing(session):
        entry = await service.update_entry(
            session, applicant_id, entry_id, body.model_dump(include=body.model_fields_set)
        )
    return entry_response(entry)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_entry(session, applicant_id, entry_id)
    return Response(status_code=204)


@router.post("/entries/delete", status_code=204)
async def delete_entries(
    body: DeleteMany,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_entries(session, applicant_id, body.ids)
    return Response(status_code=204)


@router.get("/entries/{entry_id}/resumes")
async def entry_resumes(
    entry_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    try:
        count = await built_resumes.count_showing_entry(session, applicant_id, entry_id)
    except service.NotFound:
        raise HTTPException(404, "Not found in your experience bank")
    return {"built_resumes": count}


@router.post("/entries/{entry_id}/bullets", status_code=201, response_model=BulletResponse)
async def add_bullet(
    entry_id: uuid.UUID,
    body: BulletCreate,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> BulletResponse:
    async with _writing(session):
        bullet = await service.add_bullet(session, applicant_id, entry_id, body.text)
    return BulletResponse.model_validate(bullet)


@router.patch("/bullets/{bullet_id}", response_model=BulletResponse)
async def update_bullet(
    bullet_id: uuid.UUID,
    body: BulletUpdate,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> BulletResponse:
    async with _writing(session):
        bullet = await service.update_bullet(
            session, applicant_id, bullet_id, text=body.text, position=body.position
        )
    return BulletResponse.model_validate(bullet)


@router.delete("/bullets/{bullet_id}", status_code=204)
async def delete_bullet(
    bullet_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_bullet(session, applicant_id, bullet_id)
    return Response(status_code=204)


@router.post("/skills", status_code=201, response_model=SkillResponse)
async def add_skill(
    body: SkillCreate,
    resume_id: uuid.UUID | None = None,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    async with _writing(session):
        owner, built = await _target(session, applicant_id, resume_id)
        skill = await service.add_skill(session, applicant_id, body.name, body.group, resume_id=owner)
        # Added by hand: a skill removed before is the student's again (KAN-369).
        await service.forget_removed(session, applicant_id, body.name)
        if built is not None:
            await built_resumes.update_choices(
                session, applicant_id, built, skills=[{"skill_id": skill.id, "shown": True}]
            )
    return service.skill_response(skill, [i for i in (owner, built) if i is not None])


@router.patch("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdate,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    async with _writing(session):
        skill = await service.update_skill(
            session, applicant_id, skill_id, body.model_dump(include=body.model_fields_set)
        )
    return SkillResponse.model_validate(skill)


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_skill(session, applicant_id, skill_id)
    return Response(status_code=204)


@router.post("/skills/delete", status_code=204)
async def delete_skills(
    body: DeleteMany,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_skills(session, applicant_id, body.ids)
    return Response(status_code=204)


@router.post("/sections", status_code=201, response_model=CustomSectionResponse)
async def create_section(
    body: CustomSectionCreate,
    resume_id: uuid.UUID | None = None,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> CustomSectionResponse:
    async with _writing(session):
        # Under a built resume the section is the student's own: a built
        # resume shows entries, never sections (KAN-498)
        owner, _ = await _target(session, applicant_id, resume_id)
        section = await service.create_section(session, applicant_id, body.name, body.layout, resume_id=owner)
    return service.section_response(section, [owner] if owner else [])


@router.patch("/sections/{section_id}", response_model=CustomSectionResponse)
async def rename_section(
    section_id: uuid.UUID,
    body: CustomSectionUpdate,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> CustomSectionResponse:
    async with _writing(session):
        section = await service.rename_section(session, applicant_id, section_id, body.name)
        response = service.section_response(section, [section.resume_id] if section.resume_id else [])
    return response


@router.delete("/sections/{section_id}", status_code=204)
async def delete_section(
    section_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with _writing(session):
        await service.delete_section(session, applicant_id, section_id)
    return Response(status_code=204)


async def _resume_to_import(session: AsyncSession, applicant_id: uuid.UUID, resume_id: uuid.UUID | None) -> Resume:
    from app.queries.bank import resume_to_import
    resume = await resume_to_import(session, applicant_id, resume_id)
    if resume is None:
        raise HTTPException(404, "Upload a resume to import it")
    return resume


async def _text_again(resume: Resume) -> str | None:
    """The upload's text extracted again from its file, so Import Again
    reads it as an upload is read today (KAN-809): an upload from before a
    fix to text extraction kept its old text (words with no space between
    them before KAN-303's `pdf_spaces`, 2026-11-05), and Import Again read
    that again. The stored text when the file cannot be read or holds none:
    Import Again never fails over Storage."""
    if not resume.storage_path:
        return resume.raw_text
    try:
        contents = await stored_files.read(get_supabase, resume.storage_path)
        again = await extract(contents, PurePosixPath(resume.storage_path).suffix.lower()) if contents else None
    # Storage down, or the file refused by extraction: the stored text stands
    except Exception as exc:
        logger.warning("Import Again read the stored text: the file could not be read again: %r", exc)
        return resume.raw_text
    return again or resume.raw_text


async def _keep_text(session: AsyncSession, applicant_id: uuid.UUID, resume: Resume, raw_text: str | None) -> None:
    """The text read again, stored with its hash (routers/resumes.py's
    `text_hash`), so the next read and the duplicate check see it. The hash
    stays empty when another upload of the student holds it: the two are
    one resume, and the hash is unique per student."""
    from app.routers.resumes import _duplicate_of, text_hash

    if raw_text == resume.raw_text:
        return
    digest = text_hash(raw_text)
    taken = await _duplicate_of(session, applicant_id, digest, besides=resume.id)
    resume.raw_text, resume.text_hash = raw_text, None if taken is not None else digest


@router.post("/import", response_model=ImportResponse)
async def import_resume(
    body: ImportRequest,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    account: AuthenticatedAccount = Depends(get_current_account),
    llm: LLM = Depends(get_llm),
    session: AsyncSession = Depends(get_session),
) -> ImportResponse:
    resume = await _resume_to_import(session, applicant_id, body.resume_id)
    # The file read again, so a resume uploaded before a fix to extraction
    # or the parser gets the fix (`_text_again`). The AI use, if any,
    # commits with the bank writes below. The parser's custom sections
    # (KAN-498) come through the combined reading: the AI reads only the
    # fixed sections, so they have no twin there.
    raw_text = await _text_again(resume)
    reading, left = await read_upload(session, applicant_id, account, raw_text, llm)
    async with _writing(session):
        await _keep_text(session, applicant_id, resume, raw_text)
        imported = await service.import_upload(session, applicant_id, resume.id, reading.entries, reading.skills)
        # Import Again reads the header too (KAN-436), filling only the
        # profile's empty fields, as an upload does
        header = await header_fill.fill_from_header(session, applicant_id, raw_text)
    return ImportResponse(
        resume_id=resume.id,
        filename=resume.original_filename,
        found=len(reading.entries) + len(reading.skills),
        entries_added=imported.entries_added,
        skills_added=imported.skills_added,
        read_by=reading.read_by,
        uses_left=left,
        header=header,
    )

