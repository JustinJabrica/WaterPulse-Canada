#!/bin/bash
# =============================================================================
# WaterPulse Backend — Container Entrypoint
# =============================================================================
#
# This script runs every time the backend container starts. It ensures the
# database is ready and the schema is up to date before the API server begins
# accepting requests.
#
# Sequence:
#   1. Wait for PostgreSQL to accept connections (up to 60 seconds)
#   2. Run Alembic migrations to bring the schema to the latest version
#   3. Start uvicorn, passing through any extra arguments from docker-compose
#      (e.g., --reload for development hot-reloading)
#
# Why wait for the database?
#   Docker Compose starts services roughly in parallel. Even with depends_on
#   and healthchecks, there can be a brief gap between PostgreSQL accepting
#   TCP connections and being ready to handle queries. This retry loop
#   prevents Alembic from failing on the first attempt.
#
# Why "exec" before uvicorn?
#   "exec" replaces the shell process with uvicorn, so Docker stop signals
#   (SIGTERM) reach uvicorn directly for graceful shutdown. Without exec,
#   the shell would receive the signal and uvicorn might be killed abruptly.
#
# IMPORTANT: This file MUST use LF line endings (not CRLF) to run inside
# the Linux container. The .gitattributes rule "*.sh text eol=lf" ensures
# this is handled automatically by git.
# =============================================================================

set -e    # Exit immediately if any command fails

# ── Step 1: Wait for PostgreSQL ──────────────────────────────────────────────
# Uses psycopg2 to verify PostgreSQL accepts queries (not just TCP connections).
# Retries every 2 seconds for up to 30 attempts (60 seconds total).
# Connection params come from environment variables set in docker-compose.yml.
# We use individual params instead of DATABASE_URL_SYNC because the SQLAlchemy
# dialect prefix (postgresql+psycopg2://) is not valid for raw psycopg2.
echo "Waiting for database..."
for i in $(seq 1 30); do
    python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(
        host='db',
        port=5432,
        user='waterpulse',
        dbname='waterpulse',
        password=os.environ['POSTGRES_PASSWORD'],
    )
    conn.close()
except Exception:
    exit(1)
" 2>/dev/null && break
    echo "  Database not ready, retrying in 2s... ($i/30)"
    sleep 2
done

# ── Step 2: Run Alembic migrations ───────────────────────────────────────────
# "alembic upgrade head" applies all pending migrations to bring the schema
# to the latest version. If migrations fail, set -e ensures the container
# stops here — the API will NOT start with an outdated schema.
# alembic.ini and alembic/ are copied into /app by the Dockerfile.
echo "Running Alembic migrations..."
alembic upgrade head

# ── Step 3: Start the API server ─────────────────────────────────────────────
# uvicorn serves the FastAPI app on all interfaces (0.0.0.0) so it's
# reachable from other containers and the host machine.
# "$@" passes extra arguments from docker-compose "command" — in development,
# this is "--reload" for automatic restart on code changes.
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
