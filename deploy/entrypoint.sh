#!/bin/sh
# Refuse to start on the internet without a password.
if [ -z "$STUDIO_PASSWORD" ] && [ "$STUDIO_ALLOW_NO_PASSWORD" != "1" ]; then
  echo "ERROR: set STUDIO_PASSWORD (at least 10 characters) before exposing the studio." >&2
  exit 1
fi
if [ -n "$STUDIO_PASSWORD" ] && [ ${#STUDIO_PASSWORD} -lt 10 ]; then
  echo "ERROR: STUDIO_PASSWORD must be at least 10 characters." >&2
  exit 1
fi
exec python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}" \
     --proxy-headers --forwarded-allow-ips="*" --timeout-keep-alive 75
