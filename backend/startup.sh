#!/bin/sh
set -e

echo "Waiting for database + running alembic migrations..."

TRIES=0
MAX_TRIES=12
SLEEP=3

until alembic upgrade head; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -ge "$MAX_TRIES" ]; then
    echo "alembic upgrade failed after $TRIES attempts"
    exit 1
  fi
  echo "alembic upgrade failed (attempt $TRIES). Retrying in ${SLEEP}s..."
  sleep $SLEEP
done

echo "Migrations applied. Starting application."

exec uvicorn main:app --host 0.0.0.0 --port 8000
