#!/usr/bin/env bash
# Start Al Basmah AI Media Studio on http://0.0.0.0:8000
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
exec python3 -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" "$@"
