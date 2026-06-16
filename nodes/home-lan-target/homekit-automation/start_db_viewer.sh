#!/usr/bin/env bash
set -euo pipefail

DB="${COMEANDGO_DB:-/opt/presence-relay/home-lan-target/db/homekit.sqlite}"
HOST="${COMEANDGO_HOST:-127.0.0.1}"
PORT="8001"

exec python3 -m datasette "$DB" --host "$HOST" --port "$PORT"

# Keep this viewer bound to loopback unless you have reviewed the exposure.
# http://127.0.0.1:8001
