"""
apply_reports' queries, behind routers/apply_reports.py and routers/apply_app.py: store one report a student
sent from WorkIt Auto Apply (models/apply_reports.py), and the admins' list, read and delete (D26, KAN-837).
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.models.apply_reports import Apply_Report
from app.models.profiles import Applicant_Profile
from app.schemas.apply_reports import ApplyReportRequest


async def store_report(db: AsyncSession, report: ApplyReportRequest, applicant_id: uuid.UUID) -> uuid.UUID:
    '''adds the report from this student, commits, and answers its id'''
    row = Apply_Report(
        applicant_id=applicant_id, category=report.category, contact_ok=report.contact_ok,
        application_id=report.application_id, company=report.company, role=report.role,
        posting_url=report.posting_url, outcome=report.outcome, note=report.note, files=dict(report.files),
        form_png=report.png("form.png"), after_submit_png=report.png("after-submit.png"), trace=report.trace,
    )
    db.add(row)
    await db.commit()
    return row.id


def _with_email():
    return select(Apply_Report, Applicant_Profile.email).join(
        Applicant_Profile, Applicant_Profile.id == Apply_Report.applicant_id)


async def list_reports(db: AsyncSession, limit: int = 50, offset: int = 0) -> tuple[list[tuple[Apply_Report, str]], int]:
    '''the newest reports first, each with its student's email, without their files, screenshots or Trace, and how
    many there are'''
    rows = await db.execute(_with_email().order_by(Apply_Report.created_at.desc()).limit(limit).offset(offset))
    return [(row, email) for row, email in rows], await db.scalar(select(func.count()).select_from(Apply_Report)) or 0


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> tuple[Apply_Report, str] | None:
    '''one report, whole, with its student's email'''
    found = (await db.execute(_with_email().where(Apply_Report.id == report_id).options(undefer("*")))).first()
    return (found[0], found[1]) if found else None


async def delete_report(db: AsyncSession, report_id: uuid.UUID) -> bool:
    '''deletes the report and commits; False if there is none'''
    deleted = await db.execute(delete(Apply_Report).where(Apply_Report.id == report_id))
    await db.commit()
    return deleted.rowcount > 0
