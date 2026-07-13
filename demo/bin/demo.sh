#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TMP_DIR="$ROOT/demo/tmp"
DEMO_HOME="$TMP_DIR/home"
BASE="$DEMO_HOME/homekit-automation"
QUEUE_DB="$TMP_DIR/webhook_queue.sqlite3"
READY_FILE="$TMP_DIR/ingress.ready"
PID_FILE="$TMP_DIR/ingress.pid"
INGRESS_LOG="$TMP_DIR/ingress.log"
ADAPTER_LOG="$TMP_DIR/adapter.log"
DB="$BASE/db/homekit.sqlite"
HELPER="$ROOT/demo/lib/local_demo.py"
EVENT_SH="$ROOT/nodes/home-lan-target/homekit-automation/event.sh"
INGEST="$ROOT/nodes/home-lan-target/homekit-automation/ingest_enrich.py"
DEMO_TOKEN="presence-relay-demo-token"
HOST="127.0.0.1"
PORT="18787"
export PRESENCE_RELAY_DISABLE_WEATHER=1
export PRESENCE_RELAY_DISABLE_ASYNC_ENRICH=1

cleanup_server() {
	python3 "$HELPER" stop "$PID_FILE" >/dev/null 2>&1 || true
}

if [[ "${1:-}" == "--clean" ]]; then
	cleanup_server
	python3 "$HELPER" clean "$ROOT" "$TMP_DIR"
	echo "Presence Relay demo state cleaned"
	exit 0
fi

if [[ $# -gt 0 ]]; then
	echo "usage: ./demo/bin/demo.sh [--clean]" >&2
	exit 2
fi

trap cleanup_server EXIT INT TERM

echo "Presence Relay - deterministic local demo"
echo "[1/6] Preparing disposable state"
cleanup_server
python3 "$HELPER" clean "$ROOT" "$TMP_DIR"
mkdir -p "$BASE/db"
ln -s "$INGEST" "$BASE/ingest_enrich.py"

echo "[2/6] Starting authenticated local ingress"
WEBHOOK_LISTEN_HOST="$HOST" \
WEBHOOK_LISTEN_PORT="$PORT" \
WEBHOOK_TOKEN="$DEMO_TOKEN" \
WEBHOOK_QUEUE_DB="$QUEUE_DB" \
python3 "$HELPER" serve "$ROOT" "$READY_FILE" >"$INGRESS_LOG" 2>&1 &
printf '%s\n' "$!" >"$PID_FILE"

for _ in {1..100}; do
	if [[ -f "$READY_FILE" ]]; then
		break
	fi
	if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
		echo "local ingress failed to start; see demo/tmp/ingress.log" >&2
		exit 1
	fi
	sleep 0.05
done

if [[ ! -f "$READY_FILE" ]]; then
	echo "local ingress did not become ready" >&2
	exit 1
fi

echo "[3/6] Sending leave event: sheridan-plaza"
curl -fsS -o "$TMP_DIR/leave.response" \
	-X POST "http://$HOST:$PORT/hook/homekit" \
	-H "Content-Type: application/json" \
	-H "X-Auth-Token: $DEMO_TOKEN" \
	--data-binary "@$ROOT/demo/fixtures/leave-sheridan-plaza.json"
python3 "$HELPER" deliver "$QUEUE_DB" "$DEMO_HOME" "$EVENT_SH" "$ADAPTER_LOG"

echo "[4/6] Sending arrive event: kilmer-elementary"
curl -fsS -o "$TMP_DIR/arrive.response" \
	-X POST "http://$HOST:$PORT/hook/homekit" \
	-H "Content-Type: application/json" \
	-H "X-Auth-Token: $DEMO_TOKEN" \
	--data-binary "@$ROOT/demo/fixtures/arrive-kilmer-elementary.json"
python3 "$HELPER" deliver "$QUEUE_DB" "$DEMO_HOME" "$EVENT_SH" "$ADAPTER_LOG"

echo "[5/6] Reading persisted place transitions"
sqlite3 -header -column "$DB" \
	"SELECT sequence AS seq, event, place, previous_place, current_place FROM events ORDER BY ts_epoch ASC, sequence ASC;"

echo "[6/6] Verifying expected state"
python3 "$HELPER" verify "$DB"
python3 "$HELPER" viewer-check "$ROOT" "$DB"
echo "PASS: authenticated events were processed and persisted locally"
