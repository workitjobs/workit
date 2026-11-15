# Coding Standards

The reviewer loads this file through `@.sandcastle/CODING_STANDARDS.md`. The
source of truth is the repo's own guidance: the root `CLAUDE.md` and the
`CLAUDE.md` of each tier the diff touches (`frontend/`, `backend/`,
`scraper/`). Read those and review against them. The rules most often broken:

## Layout

- Dependencies belong to their tier: `npm install` in `frontend/`, `uv add` in
  `backend/` or `scraper/`. Never at the repo root.
- Only `backend/` talks to the database. No ORM, connection string or schema in
  the frontend; a query in a React component belongs in an endpoint.
- Alembic owns the schema. `scraper/` never issues DDL. Never run
  `alembic upgrade`: people apply migrations.

## Cross-platform

- No shell-specific npm scripts: no `rm -rf`, `&&` chains, `$(...)` or `cd`.
- Build paths with `node:path`, never by joining with `/`.
- LF line endings only.

## Testing

- New or changed behaviour has a test, written before the code.
