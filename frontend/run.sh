#!/usr/bin/env bash
# Builds and serves the frontend natively (no Docker) — used for both local
# dev and the NAS. Set VITE_API_URL before building so the browser knows
# where the API lives (e.g. http://<nas-lan-ip>:8000).
set -euo pipefail
cd "$(dirname "$0")"

npm install
npm run build
exec npx serve -s dist -l "${PORT:-4173}"
