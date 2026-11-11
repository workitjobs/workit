# The API as one image, for the Cloudflare Container (ADR 0004, KAN-295).
# Build from the REPO ROOT, because ../scout and ../scraper are path dependencies:
#     docker build --platform linux/amd64 -f backend/Dockerfile -t workit-api .
# Every COPY names its paths, never a whole folder: `wrangler deploy` pipes
# this file in on stdin (`-f -`), so BuildKit never finds
# Dockerfile.dockerignore and a laptop's backend/.venv and vendor/ would land
# on top of the image's. backend/CLAUDE.md, Deployment, has the rules.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv

# pyproject.toml asks for a uv-managed interpreter (laptops); in the image the
# base's own 3.12 is the pinned one, so uv uses it instead of downloading one.
# Bytecode is compiled once here, not on every cold start.
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 api
WORKDIR /app/backend

# Dependencies first, so a code-only change reuses this layer
COPY scout/pyproject.toml /app/scout/
COPY scout/workit_scout /app/scout/workit_scout
# The scraper package (KAN-605) and its board catalog, which
# app/scraper/schedules.py reads at /app/scraper/boards.csv
COPY scraper/pyproject.toml scraper/boards.csv /app/scraper/
COPY scraper/workit_scraper /app/scraper/workit_scraper
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/data ./data
COPY backend/scripts ./scripts
COPY backend/app ./app
# The Fill engine's Rules table (KAN-756, app/services/rules_table.py), from the
# fill-engine submodule its build writes it into, at the same path beside
# backend/ as in the repo. The deploy checks the submodule out; without it
# this COPY fails the build, so production never runs without the table.
COPY autofiller_extension/fill-engine/dist/rules-table.json /app/autofiller_extension/fill-engine/dist/rules-table.json
# Pinned Tectonic and its warm cache into vendor/tectonic/. Owned by the
# runtime user: Tectonic writes into its cache even offline, so a writable
# cache is used in place (no copy to /tmp)
RUN .venv/bin/python scripts/fetch_tectonic.py && chown -R api:api vendor

# Keep connections open across requests (app/config.py, db_pool_size)
ENV DB_POOL_SIZE=5

USER api
EXPOSE 8080
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
