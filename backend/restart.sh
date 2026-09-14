#!/usr/bin/env bash
# Restarts the backend: run_app.sh already stops any previously backgrounded
# instance (via logs/backend.pid) before starting a new one, so this is just
# an explicit entry point for that behavior.
set -euo pipefail
cd "$(dirname "$0")"
exec ./run_app.sh
