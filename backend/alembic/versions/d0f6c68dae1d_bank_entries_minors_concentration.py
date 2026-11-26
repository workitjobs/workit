"""bank entries: minors and a concentration, apart from the major (KAN-891)

Revision ID: d0f6c68dae1d
Revises: 74b507514e4a
Create Date: 2026-11-16 18:30:00.000000

Chained after KAN-898's `74b507514e4a` (the reading log): both were
written on `36d339a2d6b4` in parallel, and two heads fail `upgrade head`.

A school's minors (`minors`, a text[] of names, '{}' by default, as
`coursework` is) and its concentration (`concentration`, with the resume's
own word: "Concentration in Human-Computer Interaction", "Specialization in
AI/ML", "Track in Systems", "Emphasis in X"). Only Education holds them
(`bank_entries_study_check`, as `schemas/bank.py`'s SECTION_FIELDS says).

Until now an entry had only a field of study, and the parser and the AI
reading wrote a minor and a specialization into it ("Computer Science,
minor in Economics, specialization in AI/ML"), so a form's Discipline got
the whole line. The data step moves them out of every school's field of
study by the parser's rule (`resume_parser.split_study`): a part starts at
its word (Minor, Minors, Double Minor, Concentration, Specialization,
Emphasis, Track) with "in" or ":", with what joins it (", ", "|", "(",
"with a", "and a"); the text before the first part stays the major; honors
written after a part go back to the major (KAN-813); a minor list splits at
commas, and a plural or double one at "and" too. `tests/test_minors.py`
runs MOVE on seeded rows and checks each against `split_study`.

Apply it before the deploy that maps the columns: every entry INSERT names
them and every bank read selects them, so deployed first, uploads, Import
Again, Add, the Experiences page, Generate and every resume answer 500. The
old code reads the moved rows' major alone and never sees the minors, which
is safe, so applying it early is safe. `models/bank.py` changed, so the bank
job needs a pull and a restart after the merge (backend/CLAUDE.md,
Deployment).

Downgrade writes the minors and the concentration back into the field of
study in the parser's old form ("..., minor in X, concentration in Y"),
then drops the columns.
"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd0f6c68dae1d'
down_revision: Union[str, Sequence[str], None] = '74b507514e4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `resume_parser._STUDY_PART_RE` in Postgres's own regex syntax: \m and \M
# are a word's start and end. Keep the two the same.
_PART = (
    r"\s*(?:[,;|–—-]\s*|\(\s*|\m(?:with|plus|and)\s+(?:an?\s+)?)?"
    r"\m((?:double\s+)?minors?|specialization|concentration|emphasis|track)\M\s*(?:in\M|:)\s*"
)
# `resume_parser._HONOR_AFTER_FIELD_RE`
_HONOR = (
    r",\s*((?:with\s+)?(?:(?:highest|high)\s+)?hono(?:u)?rs(?:\s+program)?"
    r"|(?:(?:summa|magna)\s+)?cum\s+laude)\y(?!\s*:)"
)

# Each school whose field of study holds a part: chr(1) before each part's
# word and chr(2) after it, so piece 1 is the major and each later piece is
# "word<2>value". `move()` puts the patterns in, each ":" escaped, since
# SQLAlchemy's text() reads "?:in" as a value named "in". Inlined, not bound:
# offline (`--sql`) a bound pattern prints with its backslashes doubled, so
# the printed SQL would not be the SQL that runs.
_MOVE = r"""
WITH marked AS (
    SELECT id, string_to_array(
        regexp_replace(field_of_study, :part, chr(1) || '\1' || chr(2), 'gi'), chr(1)) AS pieces
    FROM bank_entries
    WHERE section = 'education' AND field_of_study ~* :part
),
raw_parts AS (
    SELECT m.id, p.n,
           lower(regexp_replace(split_part(p.piece, chr(2), 1), :spaces, ' ', 'g')) AS kind,
           split_part(p.piece, chr(2), 2) AS value
    FROM marked AS m, unnest(m.pieces[2:]) WITH ORDINALITY AS p(piece, n)
),
cut_parts AS (
    SELECT id, n, kind,
           (regexp_match(value, :honor, 'i'))[1] AS honor,
           btrim(regexp_replace(value, :honor_on, '', 'i'), ' ' || chr(9) || ',;|') AS value
    FROM raw_parts
),
parts AS (
    SELECT id, n, kind, honor,
           CASE WHEN right(value, 1) = ')'
                 AND length(value) - length(replace(value, ')', '')) > length(value) - length(replace(value, '(', ''))
                THEN rtrim(left(value, -1), ' ,;')
                ELSE value END AS value
    FROM cut_parts
),
minor_items AS (
    SELECT p.id, p.n * 1000 + i.k AS pos, btrim(i.item) AS item
    FROM parts AS p,
         unnest(regexp_split_to_array(p.value, CASE WHEN p.kind ~ '^(minors|double)' THEN :many ELSE :one END))
             WITH ORDINALITY AS i(item, k)
    WHERE p.kind LIKE '%minor%' AND p.value <> '' AND btrim(i.item) <> ''
),
minors AS (
    SELECT id, array_agg(item ORDER BY pos) AS minors
    FROM (SELECT DISTINCT ON (id, lower(item)) id, item, pos FROM minor_items ORDER BY id, lower(item), pos) AS once
    GROUP BY id
),
studies AS (
    SELECT m.id,
           nullif(concat_ws(', ',
                            nullif(btrim(m.pieces[1], ' ' || chr(9) || ',;|–—-('), ''),
                            (SELECT string_agg(p.honor, ', ' ORDER BY p.n) FROM parts AS p
                             WHERE p.id = m.id AND p.honor IS NOT NULL)), '') AS major,
           (SELECT string_agg(upper(left(p.kind, 1)) || substr(p.kind, 2) || ' in ' || p.value, ', ' ORDER BY p.n)
            FROM parts AS p
            WHERE p.id = m.id AND p.kind NOT LIKE '%minor%' AND p.value <> '') AS concentration
    FROM marked AS m
)
UPDATE bank_entries AS e
SET field_of_study = s.major,
    minors = coalesce(mi.minors, '{}'),
    concentration = s.concentration
FROM studies AS s
LEFT JOIN minors AS mi ON mi.id = s.id
WHERE e.id = s.id
"""
PATTERNS = {
    "part": _PART,
    "honor": _HONOR,
    # from the honor to the value's end
    "honor_on": _HONOR + ".*$",
    "spaces": r"\s+",
    # a plural or double minor's list splits at "and" too
    "many": r"\s*,\s*(?:and\s+)?|\s+and\s+",
    "one": r"\s*,\s*",
}


def _literal(pattern: str) -> str:
    # standard_conforming_strings is on (Postgres's default since 9.1, and
    # Supabase's), so a backslash in a literal is itself
    return "'" + pattern.replace("'", "''").replace(":", "\\:") + "'"


MOVE = re.sub(r":(\w+)", lambda m: _literal(PATTERNS[m[1]]), _MOVE)


def move() -> sa.TextClause:
    """MOVE as `op.execute` and the test run it."""
    return sa.text(MOVE)


# The downgrade's way back: the parser's old form, "Computer Science, minor
# in Economics, concentration in HCI", clipped to the field's 200 characters
JOIN = """
UPDATE bank_entries
SET field_of_study = left(nullif(concat_ws(', ',
        field_of_study,
        CASE WHEN cardinality(minors) > 0 THEN 'minor in ' || array_to_string(minors, ', ') END,
        lower(left(concentration, 1)) || substr(concentration, 2)), ''), 200)
WHERE minors <> '{}' OR concentration IS NOT NULL
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bank_entries', sa.Column(
        'minors', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False))
    op.add_column('bank_entries', sa.Column('concentration', sa.String(), nullable=True))
    op.execute(move())
    op.create_check_constraint(
        'bank_entries_study_check', 'bank_entries',
        "section = 'education' OR (minors = '{}' AND concentration IS NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('bank_entries_study_check', 'bank_entries', type_='check')
    op.execute(JOIN)
    op.drop_column('bank_entries', 'concentration')
    op.drop_column('bank_entries', 'minors')
