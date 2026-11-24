"""
WorkIt Auto Apply's Send report (D26, KAN-837; W1 of docs/desktop_application_auto_apply.md): the support form in
the app's window, opened from Settings or from an Application's tile. The student picks what it is about, writes
what happened and says whether WorkIt may email them; when they include an Application, the app also sends its
Record and its Trace, with the student's private values masked in the app (apply-agent/src/apply/report.py). Never
sent automatically. The team reads it to fix the problem it shows, then deletes it: a report has no retention period,
since the privacy policy says WorkIt keeps it until its problem is fixed.

POST /apply-app/reports  ApplyReportRequest (app/schemas/apply_reports.py), from a student's account
     Stores it with its sender and answers {"id"} (201). 403 for an account that is not a student's. 413 past
     BODY_MAX bytes (read in chunks, never whole), 422 for a key outside the shape, a file name the Record does not
     have, or a screenshot that is not a PNG. 429 past the account's daily cap (APPLY_REPORT_DAILY_CAP,
     app/services/daily_caps.py).
GET  /admin/apply-reports            ?limit=&offset=: newest first, each with its student's email (for a reply when
     contact_ok), without files, screenshots or Trace (admins only, 403)
GET  /admin/apply-reports/{id}       one, whole: its files, the screenshots it has, its Trace
GET  /admin/apply-reports/{id}/screenshots/{name}  form.png or after-submit.png, as image/png
DELETE /admin/apply-reports/{id}     its problem is fixed, or the team drops it: the report is deleted (204)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_admin
from app.models.apply_reports import Apply_Report
from app.queries.apply_reports import (
    delete_report,
    get_report,
    list_reports,
    store_report,
)
from app.routers.apply_app import _student
from app.schemas.apply_reports import (
    BODY_MAX,
    ApplyReportDetail,
    ApplyReportList,
    ApplyReportRequest,
    ApplyReportStored,
    ApplyReportSummary,
    Screenshot,
)
from app.schemas.auth import AuthenticatedAccount
from app.services.daily_caps import Capped, take_daily

router = APIRouter(tags=["apply-reports"])

TOO_LARGE = f"A report is at most {BODY_MAX // 1_000_000} MB."


async def _report_body(request: Request) -> ApplyReportRequest:
    """The request's report, read at most BODY_MAX bytes (413 past it, whatever Content-Length says)."""
    if int(request.headers.get("content-length") or 0) > BODY_MAX:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, TOO_LARGE)
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > BODY_MAX:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, TOO_LARGE)
    try:
        return ApplyReportRequest.model_validate_json(bytes(body))
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            error.errors(include_url=False, include_input=False, include_context=False)) from None


def _summary(row: Apply_Report, email: str) -> dict:
    return {"id": str(row.id), "created_at": row.created_at, "applicant_id": str(row.applicant_id), "email": email,
            "category": row.category, "contact_ok": row.contact_ok, "application_id": row.application_id, "company": row.company, "role": row.role,
            "posting_url": row.posting_url, "outcome": row.outcome, "note": row.note}


async def _found(db: AsyncSession, report_id: uuid.UUID) -> tuple[Apply_Report, str]:
    found = await get_report(db, report_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such report.")
    return found


@router.post("/apply-app/reports", response_model=ApplyReportStored, status_code=status.HTTP_201_CREATED)
async def send_report(
    request: Request,
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
) -> ApplyReportStored:
    """Stores one Application's report from the signed-in student."""
    body = await _report_body(request)
    await take_daily(db, account.id, Capped.APPLY_REPORT)
    return ApplyReportStored(id=str(await store_report(db, body, account.id)))


@router.get("/admin/apply-reports", response_model=ApplyReportList)
async def all_apply_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplyReportList:
    rows, total = await list_reports(db, limit, offset)
    return ApplyReportList(reports=[ApplyReportSummary(**_summary(r, email)) for r, email in rows], total=total)


@router.get("/admin/apply-reports/{report_id}", response_model=ApplyReportDetail)
async def one_apply_report(
    report_id: uuid.UUID,
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplyReportDetail:
    row, email = await _found(db, report_id)
    screenshots = [name for name, png in (("form.png", row.form_png), ("after-submit.png", row.after_submit_png)) if png]
    return ApplyReportDetail(**_summary(row, email), files=row.files or {}, screenshots=screenshots, trace=row.trace)


@router.get("/admin/apply-reports/{report_id}/screenshots/{name}")
async def apply_report_screenshot(
    report_id: uuid.UUID,
    name: Screenshot,
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> Response:
    row, _ = await _found(db, report_id)
    png = row.form_png if name == "form.png" else row.after_submit_png
    if not png:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"The report has no {name}.")
    return Response(png, media_type="image/png")


@router.delete("/admin/apply-reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def fixed_apply_report(
    report_id: uuid.UUID,
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Its problem is fixed, or the team drops it: the report goes, as the privacy policy says."""
    if not await delete_report(db, report_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such report.")
