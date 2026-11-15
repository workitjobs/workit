# Coding Standards

The reviewer loads this file through `@.sandcastle/CODING_STANDARDS.md`. The
source of truth is the repo's own guidance: the root `CLAUDE.md` and the
`CLAUDE.md` of each folder the diff touches. Read those and review against them. The rules most often broken:

## Layout

- Dependencies belong to their folder: `npm install` in `frontend/`, `uv add`
  in the Python package. Never at the repo root. `scraper/` is standard
  library only.
- Only `backend/` talks to the database. No ORM, connection string or schema in
  the frontend; a query in a React component belongs in an endpoint.
- Alembic owns the schema. Never run `alembic upgrade`: people apply
  migrations.
- A change updates the nearest `CLAUDE.md` in the same commit.

## Cross-platform

- No shell-specific npm scripts: no `rm -rf`, `&&` chains, `$(...)` or `cd`.
- Build paths with `node:path`, never by joining with `/`.
- LF line endings only.

## Testing

- New or changed behaviour has a test, written before the code.
