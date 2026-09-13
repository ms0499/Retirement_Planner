#!/usr/bin/env bash
# Runs the API natively (no Docker) — used for both local dev and the NAS.
# Requires: a venv at ./.venv with requirements.txt installed, and a .env
# file (see .env.example) with DATABASE_URL pointed at your Postgres instance.
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate
alembic upgrade head
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --access-logfile - \
  --error-logfile -
