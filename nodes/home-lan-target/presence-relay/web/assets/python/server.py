#!/usr/bin/env python3
# vim: set noexpandtab tabstop=4 shiftwidth=4:

import html
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

BASE = Path.home() / "presence-relay" / "web"
ASSETS_DIR = BASE / "assets"

DB_PATH = Path(os.environ.get("COMEANDGO_DB", str(Path.home() / "presence-relay" / "db" / "presence.sqlite")))
LISTEN_HOST = os.environ.get("COMEANDGO_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("COMEANDGO_PORT", "8002"))

DEFAULT_LIMIT = int(os.environ.get("COMEANDGO_DEFAULT_LIMIT", "200"))
MAX_LIMIT = int(os.environ.get("COMEANDGO_MAX_LIMIT", "2000"))

INDEX_HTML = BASE / "index.html"


def db_connect() -> sqlite3.Connection:
	conn = sqlite3.connect(str(DB_PATH))
	conn.row_factory = sqlite3.Row
	return conn


def clamp(n: int, lo: int, hi: int) -> int:
	if n < lo:
		return lo
	if n > hi:
		return hi
	return n


def _guess_content_type(path: Path) -> str:
	s = path.suffix.lower()
	if s == ".css":
		return "text/css; charset=utf-8"
	if s == ".js":
		return "text/javascript; charset=utf-8"
	if s == ".html":
		return "text/html; charset=utf-8"
	if s == ".png":
		return "image/png"
	if s in (".jpg", ".jpeg"):
		return "image/jpeg"
	if s == ".svg":
		return "image/svg+xml"
	return "application/octet-stream"


def _safe_asset_path(url_path: str) -> Optional[Path]:
	# url_path like: "/assets/css/main.css"
	prefix = "/assets/"
	if not url_path.startswith(prefix):
		return None

	rel = url_path[len(prefix):]
	rel = rel.lstrip("/")

	# Resolve and ensure it stays within ASSETS_DIR
	target = (ASSETS_DIR / rel).resolve()
	base = ASSETS_DIR.resolve()

	# Python <3.9 compatible "is_relative_to" check
	try:
		target.relative_to(base)
	except Exception:
		return None

	if not target.exists() or not target.is_file():
		return None

	return target


def fetch_events(limit: int) -> List[Dict[str, Any]]:
	limit = clamp(limit, 1, MAX_LIMIT)
	place_expr = "'unnamed' AS place"
	previous_place_expr = "'unnamed' AS previous_place"
	current_place_expr = "'unnamed' AS current_place"
	enrichment_status_expr = "NULL AS enrichment_status"
	environmental_hour_utc_expr = "NULL AS environmental_hour_utc"
	weather_temp_label_expr = "NULL AS weather_temp_label"

	conn = db_connect()
	try:
		cols = {row["name"] for row in conn.execute("PRAGMA table_info(events);").fetchall()}
		if "place" in cols:
			place_expr = "COALESCE(place, 'unnamed') AS place"
		if "previous_place" in cols:
			previous_place_expr = "COALESCE(previous_place, 'unnamed') AS previous_place"
		if "current_place" in cols:
			current_place_expr = "COALESCE(current_place, 'unnamed') AS current_place"
		if "enrichment_status" in cols:
			enrichment_status_expr = "enrichment_status"
		if "environmental_hour_utc" in cols:
			environmental_hour_utc_expr = "environmental_hour_utc"
		if "weather_temp_label" in cols:
			weather_temp_label_expr = "weather_temp_label"

		q = f"""
		SELECT
			ts_epoch,
			ts_iso,
			sequence,
			previous_status,
			new_status,
			changed,
			event,
			{place_expr},
			{previous_place_expr},
			{current_place_expr},
			dt_s,
			lat,
			lon,
			source,
			version,
			is_day,
			light_pattern,
			weather_temp_f,
			{enrichment_status_expr},
			{environmental_hour_utc_expr},
			{weather_temp_label_expr}
		FROM events
		ORDER BY ts_epoch DESC
		LIMIT ?
	"""

		rows = conn.execute(q, (limit,)).fetchall()
	finally:
		conn.close()

	out: List[Dict[str, Any]] = []
	for r in rows:
		out.append({k: r[k] for k in r.keys()})
	return out


def _fmt_num(x: Any, ndigits: int = 0) -> str:
	if x is None:
		return "-"
	try:
		if ndigits <= 0:
			return str(int(x))
		return f"{float(x):.{ndigits}f}"
	except Exception:
		return str(x)


def _fmt_latlon(x: Any) -> str:
	if x is None:
		return "-"
	try:
		return f"{float(x):.6f}"
	except Exception:
		return str(x)


def _build_rows_tbody(events: List[Dict[str, Any]]) -> str:
	lines: List[str] = []

	for e in events:
		ts_iso = html.escape(str(e.get("ts_iso") or ""))
		event = str(e.get("event") or "")
		event_safe = html.escape(event)
		place = html.escape(str(e.get("place") or "unnamed"))
		previous_place = html.escape(str(e.get("previous_place") or "unnamed"))
		current_place = html.escape(str(e.get("current_place") or "unnamed"))

		prev = html.escape(str(e.get("previous_status") or ""))
		new = html.escape(str(e.get("new_status") or ""))

		changed = _fmt_num(e.get("changed"), 0)
		dt_s = _fmt_num(e.get("dt_s"), 0)

		lat = _fmt_latlon(e.get("lat"))
		lon = _fmt_latlon(e.get("lon"))

		is_day = _fmt_num(e.get("is_day"), 0)
		light_pattern = html.escape(str(e.get("light_pattern") or "-"))

		temp_f = "-"
		if e.get("weather_temp_f") is not None:
			temp_f = _fmt_num(e.get("weather_temp_f"), 1)

		seq = _fmt_num(e.get("sequence"), 0)
		v = _fmt_num(e.get("version"), 0)
		source = html.escape(str(e.get("source") or "-"))

		chip_class = "chip"
		if event == "arrive":
			chip_class += " arrive"
		elif event == "leave":
			chip_class += " leave"

		row = (
			"<tr>"
			f"<td class=\"col-ts\">{ts_iso}</td>"
			f"<td class=\"col-event\"><span class=\"{chip_class}\">{event_safe}</span></td>"
			f"<td class=\"col-text\">{place}</td>"
			f"<td class=\"col-text\">{previous_place}</td>"
			f"<td class=\"col-text\">{current_place}</td>"
			f"<td class=\"col-prevnew\">{prev} &rarr; {new}</td>"
			f"<td class=\"col-small\">{html.escape(str(changed))}</td>"
			f"<td class=\"col-num\">{html.escape(str(dt_s))}</td>"
			f"<td class=\"col-latlon\">{html.escape(str(lat))}</td>"
			f"<td class=\"col-latlon\">{html.escape(str(lon))}</td>"
			f"<td class=\"col-small\">{html.escape(str(is_day))}</td>"
			f"<td class=\"col-text\">{light_pattern}</td>"
			f"<td class=\"col-num\">{html.escape(str(temp_f))}</td>"
			f"<td class=\"col-small\">{html.escape(str(seq))}</td>"
			f"<td class=\"col-small\">{html.escape(str(v))}</td>"
			f"<td class=\"col-text\">{source}</td>"
			"</tr>"
		)
		lines.append(row)

	return "\n".join(lines)


def _render_index(limit: int) -> bytes:
	# Read template
	body = INDEX_HTML.read_text(encoding="utf-8", errors="replace")

	# Pull events
	events = fetch_events(limit)
	rows_tbody = _build_rows_tbody(events)
	count = len(events)

	# Basic replacements
	body = body.replace("{DB_PATH}", html.escape(str(DB_PATH)))
	body = body.replace("{COUNT}", str(count))
	body = body.replace("{LIMIT}", str(limit))
	body = body.replace("{ROWS_TBODY}", rows_tbody)

	# Select dropdown helpers
	def sel(n: int) -> str:
		return "selected" if limit == n else ""

	body = body.replace("{SEL_50}", sel(50))
	body = body.replace("{SEL_100}", sel(100))
	body = body.replace("{SEL_200}", sel(200))
	body = body.replace("{SEL_500}", sel(500))
	body = body.replace("{SEL_1000}", sel(1000))

	return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
	def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
		self.send_response(code)
		self.send_header("Content-Type", content_type)
		self.send_header("Content-Length", str(len(body)))
		self.send_header("Cache-Control", "no-store")
		self.end_headers()
		self.wfile.write(body)

	def _send_text(self, code: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
		self._send_bytes(code, text.encode("utf-8"), content_type)

	def do_GET(self) -> None:
		parsed = urlparse(self.path)
		path = parsed.path

		# Static assets
		if path.startswith("/assets/"):
			target = _safe_asset_path(path)
			if target is None:
				self._send_text(404, "not found")
				return
			self._send_bytes(200, target.read_bytes(), _guess_content_type(target))
			return

		# API
		if path == "/api/events":
			qs = parse_qs(parsed.query or "")
			limit_s = (qs.get("limit") or [""])[0].strip()

			limit = DEFAULT_LIMIT
			if limit_s.isdigit():
				limit = int(limit_s)
			limit = clamp(limit, 1, MAX_LIMIT)

			if not DB_PATH.exists():
				self._send_text(500, f"db not found: {DB_PATH}")
				return

			try:
				events = fetch_events(limit)
			except Exception as e:
				self._send_text(500, f"db error: {e}")
				return

			body = json.dumps(
				{
					"db": str(DB_PATH),
					"limit": limit,
					"count": len(events),
					"events": events,
				},
				ensure_ascii=False,
				separators=(",", ":"),
			).encode("utf-8")

			self._send_bytes(200, body, "application/json; charset=utf-8")
			return

		# Index (server-rendered)
		if path == "/" or path == "/index.html":
			if not INDEX_HTML.exists():
				self._send_text(500, f"missing {INDEX_HTML}")
				return

			qs = parse_qs(parsed.query or "")
			limit_s = (qs.get("limit") or [""])[0].strip()

			limit = DEFAULT_LIMIT
			if limit_s.isdigit():
				limit = int(limit_s)
			limit = clamp(limit, 1, MAX_LIMIT)

			if not DB_PATH.exists():
				self._send_text(500, f"db not found: {DB_PATH}")
				return

			try:
				body = _render_index(limit)
			except Exception as e:
				self._send_text(500, f"render error: {e}")
				return

			self._send_bytes(200, body, "text/html; charset=utf-8")
			return

		self._send_text(404, "not found")

	def log_message(self, fmt: str, *args) -> None:
		return


def main() -> None:
	httpd = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
	print(f"Serving DB={DB_PATH} at http://{LISTEN_HOST}:{LISTEN_PORT}/")
	httpd.serve_forever()


if __name__ == "__main__":
	main()
