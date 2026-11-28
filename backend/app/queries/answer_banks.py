"""
answer_banks' queries (models/answer_banks.py, W11): one student's Answer
bank, read with its version and merged a key at a time. No HTTP; the steps
in app/auto_apply/answer_bank.py call these and own the transaction.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Text, func, literal, literal_column, select, true
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer_banks import Answer_Bank
from app.models.profiles import Applicant_Profile

# One student's bank at most (W11's "Size": about 800 KB after 2,000 forms).
# A write past either is refused whole, never cut.
MAX_ENTRIES = 5000
MAX_BYTES = 1_000_000


class TooBig(Exception):
    pass


@dataclass(frozen=True)
class Stored:
    answers: dict
    version: int


async def fetch(db: AsyncSession, applicant_id: uuid.UUID) -> Stored | None:
    """The student's bank and its version, or None while they have no row."""
    row = (await db.execute(
        select(Answer_Bank.answers, Answer_Bank.version).where(Answer_Bank.applicant_id == applicant_id)
    )).first()
    return Stored(answers=row.answers, version=row.version) if row else None


async def fetch_version(db: AsyncSession, applicant_id: uuid.UUID) -> int | None:
    """The version alone (a reader holding it needs no answers), or None with no row."""
    return await db.scalar(select(Answer_Bank.version).where(Answer_Bank.applicant_id == applicant_id))


async def reviewed_keys(db: AsyncSession, applicant_id: uuid.UUID, keys: list[str]) -> set[str]:
    """Which of `keys` the bank holds with no review flag: the student's own
    answers (or their Claude's they reviewed)."""
    if not keys:
        return set()
    entry = func.jsonb_each(Answer_Bank.answers).table_valued("key", "value").render_derived(with_types=False)
    return set(await db.scalars(
        select(entry.c.key).select_from(Answer_Bank).join(entry, true())
        .where(Answer_Bank.applicant_id == applicant_id, entry.c.key.in_(keys),
               entry.c.value.op("->", return_type=JSONB)(literal("review")).is_(None))
    ))


async def has_profile(db: AsyncSession, applicant_id: uuid.UUID) -> bool:
    """Whether the student has a profile row, which a bank row needs. Reads
    the id alone: a profile row's JSONB columns are large."""
    return await db.scalar(select(Applicant_Profile.id).where(Applicant_Profile.id == applicant_id)) is not None


async def create(db: AsyncSession, applicant_id: uuid.UUID, answers: dict) -> None:
    """The student's first row, holding `answers`; a row already there (a
    read at the same moment made it) stays as it is. Flushes; the caller commits."""
    await db.execute(
        pg_insert(Answer_Bank).values(applicant_id=applicant_id, answers=answers)
        .on_conflict_do_nothing(index_elements=[Answer_Bank.applicant_id])
    )


async def merge(db: AsyncSession, applicant_id: uuid.UUID, written: dict, deleted: list[str]) -> int:
    """
    Adds or replaces the `written` keys, drops the `deleted` ones (a key in
    both is dropped), adds one to the version, and returns it. Raises TooBig
    when the bank after holds more than MAX_ENTRIES entries or MAX_BYTES of
    JSON: the caller rolls back, so nothing of the change stays.

    Merged in the database (|| then -), in one statement, never replaced
    from a caller's copy: two writers at once each merge into the other's
    result. The row must exist (answer_bank.py makes it first).
    """
    upsert = pg_insert(Answer_Bank).values(applicant_id=applicant_id, answers=written)
    merged = (
        Answer_Bank.answers.op("||", return_type=JSONB)(upsert.excluded.answers)
        .op("-", return_type=JSONB)(literal(deleted, ARRAY(Text)))
    )
    row = (await db.execute(
        upsert.on_conflict_do_update(
            index_elements=[Answer_Bank.applicant_id],
            set_={"answers": merged, "version": Answer_Bank.version + 1, "updated_at": func.now()},
        ).returning(
            Answer_Bank.version,
            literal_column("(SELECT count(*) FROM jsonb_object_keys(answer_banks.answers))").label("entries"),
            func.octet_length(Answer_Bank.answers.cast(Text)).label("bytes"),
        )
    )).one()
    if row.entries > MAX_ENTRIES or row.bytes > MAX_BYTES:
        raise TooBig(f"The Answer bank holds at most {MAX_ENTRIES} answers and {MAX_BYTES // 1000} KB.")
    return row.version
