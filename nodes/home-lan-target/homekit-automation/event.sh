#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# VERSION NOTES
#
# v4 (direct SSH trigger):
# - iPhone Shortcut used "Run Script over SSH" to call this script directly on the
#   home LAN target (event + lat + lon).
# - This required the phone to have VPN connectivity (WireGuard) such that it could
#   reach the home LAN target over the VPN/LAN path; if VPN was off or cellular routing was weird,
#   events could fail to deliver.
#
# v5 (webhook transport bridge; no-VPN-needed delivery from phone to home LAN target):
# - iPhone Shortcut POSTs JSON to a public HTTPS endpoint on the public relay:
#   /hook/homekit
# - lighttpd reverse-proxies /hook/homekit to a local python webhook daemon (webhookd)
#   listening on 127.0.0.1:8787.
# - webhookd validates X-Auth-Token and then relays the event to the home LAN target
#   over the configured private-side delivery path, invoking this script with:
#       event.sh arrive|leave <place> <lat> <lon> [ts]
# - Net effect: the phone no longer needs to be on the VPN to deliver events; only the
#   public relay needs network reachability to the home LAN target over the private-side path.
#
# Change date: 2026-01-14
# ------------------------------------------------------------------------------

BASE="$HOME/homekit-automation"
LOG="$BASE/automation.log"
STATE_FILE="$BASE/.homekit-home-state"
SEQ_FILE="$BASE/.homekit-home-seq"
LAST_EPOCH_FILE="$BASE/.homekit-last-epoch"
LOCK_FILE="$BASE/db/.ingest.lock"

event="${1:-}"

if [[ "$event" != "arrive" && "$event" != "leave" ]]; then
	echo "usage: $0 arrive|leave [place] [lat lon] [ts]" >&2
	exit 1
fi

normalize_place() {
	local raw="${1:-}"
	local place
	place="$(printf '%s' "$raw" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | tr '[:upper:]' '[:lower:]')"
	if [[ -z "$place" ]]; then
		place="unnamed"
	fi
	if [[ ! "$place" =~ ^[a-z0-9_-]+$ ]]; then
		echo "bad place: $raw" >&2
		exit 1
	fi
	printf '%s\n' "$place"
}

is_numberish() {
	[[ "${1:-}" =~ ^[-+]?[0-9]+([.][0-9]+)?$ ]]
}

iso_now() {
	python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"))
PY
}

epoch_from_iso() {
	python3 - "$1" <<'PY'
from datetime import datetime, timezone
import sys

value = sys.argv[1].strip()
if value.endswith("Z"):
	value = value[:-1] + "+00:00"
dt = datetime.fromisoformat(value)
if dt.tzinfo is None:
	dt = dt.replace(tzinfo=timezone.utc)
print(int(dt.timestamp()))
PY
}

run_with_event_lock() {
	if command -v flock >/dev/null 2>&1; then
		exec 9>"$LOCK_FILE"
		flock 9
		_PRESENCE_RELAY_EVENT_LOCK_HELD=1 process_event
		local rc=$?
		flock -u 9
		return "$rc"
	fi

	_PRESENCE_RELAY_EVENT_LOCK_HELD=1 python3 - "$LOCK_FILE" "$0" "$@" <<'PY'
import fcntl
import os
import subprocess
import sys

lock_file = sys.argv[1]
script = sys.argv[2]
args = sys.argv[3:]
os.makedirs(os.path.dirname(lock_file), exist_ok=True)
with open(lock_file, "a", encoding="utf-8") as lock:
	fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
	subprocess.run(["bash", script] + args, check=True)
PY
}

place="unnamed"
lat=""
lon=""
ts=""

if [[ $# -ge 2 ]] && ! is_numberish "${2:-}"; then
	# New form: event.sh arrive <place> <lat> <lon> [ts]
	place="$(normalize_place "${2:-}")"
	lat="${3:-}"
	lon="${4:-}"
	ts="${5:-}"
else
	# Old form: event.sh arrive <lat> <lon> [ts]
	lat="${2:-}"
	lon="${3:-}"
	ts="${4:-}"
fi

process_event() {
	# Prefer phone-provided timestamp if present and parseable; otherwise use home LAN target clock.
	now="$(iso_now)"
	now_epoch="$(epoch_from_iso "$now")"
	ts_src="pi"

	if [[ -n "${ts:-}" ]]; then
		if ts_epoch="$(epoch_from_iso "$ts" 2>/dev/null)"; then
			now="$ts"
			now_epoch="$ts_epoch"
			ts_src="phone"
		fi
	fi

	# load and bump sequence
	if [[ -f "$SEQ_FILE" ]]; then
		read -r seq <"$SEQ_FILE"
	else
		seq=0
	fi
	seq=$((seq + 1))
	printf '%s\n' "$seq" >"$SEQ_FILE"

	# load previous state
	if [[ -f "$STATE_FILE" ]]; then
		read -r prev_state <"$STATE_FILE"
	else
		prev_state="unknown"
	fi

	case "$event" in
		arrive) new_state="home" ;;
		leave)  new_state="away" ;;
	esac

	case "$event" in
		arrive)
			previous_place="unnamed"
			current_place="$place"
			;;
		leave)
			previous_place="$place"
			current_place="unnamed"
			;;
	esac

	# seconds since last event (telemetry only)
	if [[ -f "$LAST_EPOCH_FILE" ]]; then
		read -r prev_epoch <"$LAST_EPOCH_FILE" || prev_epoch=""
	else
		prev_epoch=""
	fi

	dt_s="-"
	if [[ -n "${prev_epoch:-}" && "$prev_epoch" =~ ^[0-9]+$ ]]; then
		dt_s=$((now_epoch - prev_epoch))
	fi

	changed=0
	if [[ "$prev_state" != "$new_state" ]]; then
		changed=1
	fi

	# build the exact log line
	printf -v line '%s\tseq=%s\tprev=%s\tnew=%s\tchanged=%s\tevent=%s\tdt_s=%s\tlat=%s\tlon=%s\tts=%s\tts_src=%s\tsource=presence-relay\tv=6\tplace=%s\tprevious_place=%s\tcurrent_place=%s' \
		"$now" "$seq" "$prev_state" "$new_state" "$changed" "$event" "$dt_s" "$lat" "$lon" "$ts" "$ts_src" "$place" "$previous_place" "$current_place"

	# append to log
	printf '%s\n' "$line" >>"$LOG"

	# update state tracking
	printf '%s\n' "$new_state" >"$STATE_FILE"
	printf '%s\n' "$now_epoch" >"$LAST_EPOCH_FILE"

	# ingest+enrich exactly this one line.
	python3 "$BASE/ingest_enrich.py" --enrich --ingest-stdin --quiet <<<"$line" >/dev/null 2>&1
}

mkdir -p "$BASE/db"
if [[ "${_PRESENCE_RELAY_EVENT_LOCK_HELD:-}" == "1" ]]; then
	process_event
else
	run_with_event_lock "$@"
fi
