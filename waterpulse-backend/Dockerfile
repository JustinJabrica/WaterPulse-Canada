# =============================================================================
# WaterPulse Backend — Dockerfile
# =============================================================================
#
# Builds the FastAPI backend image with Python 3.12.
#
# Uses python:3.12-slim (Debian-based) rather than Alpine because the
# asyncpg and psycopg2-binary packages include C extensions that compile
# more reliably on Debian. The slim variant keeps the image small (~150 MB).
#
# Layer caching strategy:
#   1. Copy requirements.txt first and install dependencies
#   2. Then copy application code
#   This means changing a Python file does NOT re-trigger pip install —
#   only changes to requirements.txt invalidate the dependency layer.
#
# The entrypoint.sh script handles:
#   1. Waiting for PostgreSQL to accept queries (psycopg2 with individual
#      connection params from environment variables, not DATABASE_URL_SYNC)
#   2. Running Alembic migrations (alembic upgrade head)
#   3. Starting uvicorn (with any extra args passed via docker-compose command)
#
# Build:   docker build -t waterpulse-backend ./waterpulse-backend
# Run:     docker run -p 8000:8000 --env-file .env waterpulse-backend
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────────────────
# Copied separately from source code so this layer is cached as long as
# requirements.txt hasn't changed. --no-cache-dir saves ~50 MB of pip cache.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Copy Alembic configuration and migration scripts ─────────────────────────
# alembic.ini must be in WORKDIR because it uses relative paths.
# alembic/env.py imports app.config, so the app/ directory must also be present.
COPY alembic.ini .
COPY alembic/ alembic/

# ── Copy application source code ─────────────────────────────────────────────
COPY app/ app/

# ── Copy and prepare the entrypoint script ───────────────────────────────────
# chmod +x ensures the script is executable inside the Linux container,
# regardless of the file permissions on the Windows host.
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# ── Container configuration ──────────────────────────────────────────────────
# Port 8000 is the default uvicorn port used in entrypoint.sh.
# ENTRYPOINT runs the migration + startup script; extra args from
# docker-compose "command" (e.g., --reload) are appended via "$@".
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
