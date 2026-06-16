#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/homekit-automation"
WEB="$BASE/web"

PORT="${COMEANDGO_PORT:-8002}"

# Try to pick the primary LAN IP (route-based), fall back to hostname -I.
ip="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}' || true)"
if [[ -z "${ip:-}" ]]; then
	ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
fi
if [[ -z "${ip:-}" ]]; then
	ip="127.0.0.1"
fi

echo "presence-relay web viewer"
echo "  db:   $BASE/db/homekit.sqlite"
echo "  url:  http://${ip}:${PORT}/"
echo

cd "$WEB"
exec env \
	COMEANDGO_HOST="${COMEANDGO_HOST:-127.0.0.1}" \
	COMEANDGO_PORT="$PORT" \
	python3 ./assets/python/server.py
