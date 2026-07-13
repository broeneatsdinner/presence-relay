#!/usr/bin/env python3
import json
import os
import sqlite3
import subprocess
import threading
import time
import shlex
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LISTEN_HOST = os.environ.get("WEBHOOK_LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("WEBHOOK_LISTEN_PORT", "8787"))
AUTH_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")
QUEUE_DB = os.environ.get("WEBHOOK_QUEUE_DB", "/opt/presence-relay/var/webhook_queue.sqlite3")

PRIVATE_DELIVERY_HOST = os.environ.get("PRIVATE_DELIVERY_HOST", os.environ.get("PI_SSH_HOST", "private-delivery-host"))
PRIVATE_EVENT_COMMAND = os.environ.get("PRIVATE_EVENT_COMMAND", os.environ.get("PI_EVENT_SH", "/opt/presence-relay/home-lan-target/presence-relay/event.sh"))

DELIVER_POLL_SECONDS = float(os.environ.get("DELIVER_POLL_SECONDS", "1.0"))
SSH_CONNECT_TIMEOUT = int(os.environ.get("SSH_CONNECT_TIMEOUT", "3"))
SSH_TOTAL_TIMEOUT = int(os.environ.get("SSH_TOTAL_TIMEOUT", "8"))

MAX_BACKOFF_SECONDS = int(os.environ.get("MAX_BACKOFF_SECONDS", "600"))  # 10 minutes
MIN_BACKOFF_SECONDS = int(os.environ.get("MIN_BACKOFF_SECONDS", "5"))
PLACE_RE = re.compile(r"^[a-z0-9_-]+$")

def _now_epoch() -> int:
	return int(time.time())

def _db_connect() -> sqlite3.Connection:
	conn = sqlite3.connect(QUEUE_DB, timeout=5)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA journal_mode=WAL;")
	conn.execute("PRAGMA synchronous=NORMAL;")
	conn.execute("PRAGMA busy_timeout=5000;")
	return conn

def normalize_place(value) -> str:
	if value is None:
		return "unnamed"
	place = str(value).strip().lower()
	if not place:
		return "unnamed"
	if not PLACE_RE.fullmatch(place):
		raise ValueError("bad place")
	return place

def init_db() -> None:
	conn = _db_connect()
	try:
		conn.execute("""
			CREATE TABLE IF NOT EXISTS queue (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				created_at_epoch INTEGER NOT NULL,
				next_attempt_epoch INTEGER NOT NULL,
				attempts INTEGER NOT NULL DEFAULT 0,
				last_error TEXT,
				delivered_at_epoch INTEGER,
				event TEXT NOT NULL,
				place TEXT NOT NULL DEFAULT 'unnamed',
				lat REAL,
				lon REAL,
				raw_json TEXT NOT NULL
			);
		""")
		cols = {row["name"] for row in conn.execute("PRAGMA table_info(queue);").fetchall()}
		if "place" not in cols:
			conn.execute("ALTER TABLE queue ADD COLUMN place TEXT NOT NULL DEFAULT 'unnamed';")
		conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_pending ON queue(delivered_at_epoch, next_attempt_epoch);")
		conn.commit()
	finally:
		conn.close()

def enqueue(payload: dict) -> None:
	event = payload.get("event")
	place = payload.get("place", "unnamed")
	lat = payload.get("lat")
	lon = payload.get("lon")

	raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

	now = _now_epoch()
	conn = _db_connect()
	try:
		conn.execute("""
			INSERT INTO queue (created_at_epoch, next_attempt_epoch, attempts, last_error, delivered_at_epoch, event, place, lat, lon, raw_json)
			VALUES (?, ?, 0, NULL, NULL, ?, ?, ?, ?, ?)
		""", (now, now, str(event), str(place), lat, lon, raw))
		conn.commit()
	finally:
		conn.close()

def _compute_backoff_seconds(attempts: int) -> int:
	# attempts is incremented before computing next attempt
	# 1->5s, 2->10s, 3->20s, ... capped
	sec = MIN_BACKOFF_SECONDS * (2 ** max(0, attempts - 1))
	return int(min(MAX_BACKOFF_SECONDS, sec))

def _deliver_one(row: sqlite3.Row) -> None:
	event = row["event"]
	place = row["place"] or "unnamed"
	lat = "" if row["lat"] is None else str(row["lat"])
	lon = "" if row["lon"] is None else str(row["lon"])

	payload = {}
	try:
		if row["raw_json"]:
			payload = json.loads(row["raw_json"])
	except Exception:
		payload = {}

	ts = payload.get("ts") or ""
	ts = "" if ts is None else str(ts)
	try:
		place = normalize_place(payload.get("place", place))
	except ValueError:
		place = "unnamed"

	remote_cmd = (
		f"{shlex.quote(PRIVATE_EVENT_COMMAND)} "
		f"{shlex.quote(str(event))} "
		f"{shlex.quote(place)} "
		f"{shlex.quote(lat)} "
		f"{shlex.quote(lon)} "
		f"{shlex.quote(ts)}"
	)

	cmd = [
		"ssh",
		"-o", "BatchMode=yes",
		"-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
		PRIVATE_DELIVERY_HOST,
		remote_cmd,
	]

	try:
		subprocess.run(
			cmd,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.PIPE,
			check=True,
			timeout=SSH_TOTAL_TIMEOUT,
			text=True,
		)
		ok = True
		err = None
	except subprocess.TimeoutExpired:
		ok = False
		err = f"timeout after {SSH_TOTAL_TIMEOUT}s"
	except subprocess.CalledProcessError as e:
		ok = False
		err = (e.stderr or "").strip() or f"ssh failed rc={e.returncode}"
	except Exception as e:
		ok = False
		err = str(e)

	now = _now_epoch()

	conn = _db_connect()
	try:
		if ok:
			conn.execute("""
				UPDATE queue
				SET delivered_at_epoch = ?, last_error = NULL
				WHERE id = ?
			""", (now, row["id"]))
		else:
			new_attempts = int(row["attempts"]) + 1
			backoff = _compute_backoff_seconds(new_attempts)
			next_epoch = now + backoff
			conn.execute("""
				UPDATE queue
				SET attempts = ?, last_error = ?, next_attempt_epoch = ?
				WHERE id = ?
			""", (new_attempts, err[:500], next_epoch, row["id"]))
		conn.commit()
	finally:
		conn.close()

def delivery_worker(stop_event: threading.Event) -> None:
	while not stop_event.is_set():
		row = None
		now = _now_epoch()

		conn = _db_connect()
		try:
			row = conn.execute("""
				SELECT *
				FROM queue
				WHERE delivered_at_epoch IS NULL
				ORDER BY id ASC
				LIMIT 1
			""").fetchone()
		finally:
			conn.close()

		if row is None:
			stop_event.wait(DELIVER_POLL_SECONDS)
			continue

		if int(row["next_attempt_epoch"]) > now:
			wait_s = min(DELIVER_POLL_SECONDS, max(0.1, int(row["next_attempt_epoch"]) - now))
			stop_event.wait(wait_s)
			continue

		_deliver_one(row)

class Handler(BaseHTTPRequestHandler):
	def _send(self, code: int, body: str) -> None:
		body_b = body.encode("utf-8")
		self.send_response(code)
		self.send_header("Content-Type", "text/plain; charset=utf-8")
		self.send_header("Content-Length", str(len(body_b)))
		self.end_headers()
		self.wfile.write(body_b)

	def do_POST(self) -> None:
		parsed = urlparse(self.path)
		# /hook/presence is canonical. /hook/homekit remains a temporary
		# migration compatibility alias for older clients.
		if parsed.path not in ("/hook/presence", "/hook/homekit"):
			self._send(404, "not found")
			return

		if not AUTH_TOKEN:
			self._send(500, "server misconfigured")
			return

		got = self.headers.get("X-Auth-Token", "")
		if got != AUTH_TOKEN:
			self._send(401, "unauthorized")
			return

		cl = self.headers.get("Content-Length")
		if not cl or not cl.isdigit():
			self._send(400, "missing content-length")
			return

		try:
			raw = self.rfile.read(int(cl))
			payload = json.loads(raw.decode("utf-8"))
		except Exception:
			self._send(400, "bad json")
			return

		event = payload.get("event")
		if event not in ("arrive", "leave"):
			self._send(400, "bad event")
			return

		try:
			payload["place"] = normalize_place(payload.get("place"))
		except ValueError:
			self._send(400, "bad place")
			return

		# Queue immediately (durable) and ACK immediately.
		try:
			enqueue(payload)
		except Exception:
			self._send(500, "enqueue failed")
			return

		self._send(200, "ok")

	def log_message(self, fmt: str, *args) -> None:
		# quiet (systemd/journal already captures stdout/stderr from our code if we print)
		return

def main() -> None:
	init_db()
	stop_event = threading.Event()
	t = threading.Thread(target=delivery_worker, args=(stop_event,), daemon=True)
	t.start()

	httpd = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
	try:
		httpd.serve_forever()
	finally:
		stop_event.set()

if __name__ == "__main__":
	main()
