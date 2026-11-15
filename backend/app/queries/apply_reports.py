"""
apply_reports' queries, behind routers/apply_reports.py and routers/apply_app.py: store one report a student
sent from WorkIt Auto Apply (models/apply_reports.py), and the admins' list, read and delete (D26, KAN-837).
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.models.apply_reports import Apply_Report
from app.schemas.apply_reports import ApplyReportRequest


async def store_report(db: AsyncSession, report: ApplyReportRequest, applicant_id: uuid.UUID) -> uuid.UUID:
    '''adds the report from this student, commits, and answers its id'''
    row = Apply_Report(
        applicant_id=applicant_id, application_id=report.application_id, company=report.company, role=report.role,
        posting_url=report.posting_url, outcome=report.outcome, note=report.note, files=dict(report.files),
        form_png=report.png("form.png"), after_submit_png=report.png("after-submit.png"), trace=report.trace,
    )
    db.add(row)
    await db.commit()
    return row.id


async def list_reports(db: AsyncSession, limit: int = 50, offset: int = 0) -> tuple[list[Apply_Report], int]:
    '''the newest reports first, without their files, screenshots or Trace, and how many there are'''
    rows = await db.scalars(select(Apply_Report).order_by(Apply_Report.created_at.desc()).limit(limit).offset(offset))
    return list(rows), await db.scalar(select(func.count()).select_from(Apply_Report)) or 0


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> Apply_Report | None:
    '''one report, whole'''
    return await db.scalar(select(Apply_Report).where(Apply_Report.id == report_id).options(undefer("*")))


async def delete_report(db: AsyncSession, report_id: uuid.UUID) -> bool:
    '''deletes the report and commits; False if there is none'''
    deleted = await db.execute(delete(Apply_Report).where(Apply_Report.id == report_id))
    await db.commit()
    return deleted.rowcount > 0
