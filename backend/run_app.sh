#!/usr/bin/env bash
# Runs the API natively (no Docker) — used for both local dev and the NAS.
# Requires: a venv at ./.venv (created with PYTHON_BIN below) with
# requirements.txt installed, and a .env file (see .env.example) with
# DATABASE_URL pointed at your Postgres instance.
#
# Also serves the built frontend (see app/main.py) if ../frontend/dist
# exists, so this one process + port is all the Cloudflare Tunnel needs to
# point at (default port 6005, matching the retirement.damsm.com tunnel).
set -euo pipefail
cd "$(dirname "$0")"

# Rebuild the frontend on every run so local code changes are picked up.
# Reinstall only when package-lock.json has actually changed; `npm ci` (not
# `npm install`) does a clean reinstall from the lockfile, which avoids a
# known npm bug where optional platform-specific deps (e.g. rollup's native
# binary) get dropped when reconciling against a pre-existing node_modules
# from a different lockfile — https://github.com/npm/cli/issues/4828.
if [ -d ../frontend ]; then
  (
    cd ../frontend
    if [ ! -f node_modules/.install-stamp ] || [ package-lock.json -nt node_modules/.install-stamp ]; then
      npm ci
      touch node_modules/.install-stamp
    fi
    npm run build
  )
fi

# Pinned to match the Python version used in Dockerfile — the app relies on
# 3.9+ type-hint syntax, and other interpreters installed on the NAS (e.g. an
# older system Python or a too-new one without prebuilt wheels for our pinned
# deps) don't work here.
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3.12}"

if [ ! -x .venv/bin/python ] || ! grep -qF "$(dirname "$PYTHON_BIN")" .venv/pyvenv.cfg 2>/dev/null; then
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate
alembic upgrade head

LOG_DIR="$(pwd)/logs"
LOG_FILE="$LOG_DIR/backend.log"
PID_FILE="$LOG_DIR/backend.pid"
mkdir -p "$LOG_DIR"

# Stop a previously backgrounded instance so the port is free to rebind.
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  OLD_PID="$(cat "$PID_FILE")"
  kill "$OLD_PID"
  for _ in 1 2 3 4 5; do
    kill -0 "$OLD_PID" 2>/dev/null || break
    sleep 1
  done
fi

nohup gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT:-6005}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --access-logfile - \
  --error-logfile - \
  >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
disown

echo "Backend started in background (PID $(cat "$PID_FILE"))."
echo "Log file: $LOG_FILE"
