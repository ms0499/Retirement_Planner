#!/usr/bin/env bash
# Builds the frontend and serves it standalone on its own port — useful for
# local previews, but NOT what the NAS/tunnel deployment uses: in production
# backend/run.sh serves this same dist/ build directly (see app/main.py), so
# the Cloudflare Tunnel only has to point at one port (6005). Set
# VITE_API_URL before building only if the frontend and backend will be on
# different origins (see frontend/.env.example) — leave it unset for the
# single-origin production setup.
set -euo pipefail
cd "$(dirname "$0")"

npm install
npm run build
exec npx serve -s dist -l "${PORT:-4173}"
