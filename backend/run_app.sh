#!/usr/bin/env bash
# Runs the API natively (no Docker) — used for both local dev and the NAS.
# Requires: a venv at ./.venv with requirements.txt installed, and a .env
# file (see .env.example) with DATABASE_URL pointed at your Postgres instance.
#
# Also serves the built frontend (see app/main.py) if ../frontend/dist
# exists, so this one process + port is all the Cloudflare Tunnel needs to
# point at (default port 6005, matching the retirement.damsm.com tunnel).
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate
alembic upgrade head
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT:-6005}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --access-logfile - \
  --error-logfile -
