#!/usr/bin/env bash
set -e
export APP_HOST=${APP_HOST:-0.0.0.0}
export APP_PORT=${APP_PORT:-8000}
uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" --workers 2 --proxy-headers
