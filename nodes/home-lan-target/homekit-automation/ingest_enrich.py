#!/usr/bin/env python3
# vim: set noexpandtab tabstop=4 shiftwidth=4:
"""
ingest_enrich.py

Purpose
- Ingest ~/homekit-automation/automation.log (whitespace-delimited lines; tabs are fine)
- Store events in SQLite (schema mirrors automation.log + small enrichment)
- Optionally enrich each event with ONLY:
	- is_day (0/1)
	- light_pattern: pre-dawn, rising, noon, afternoon, setting, twilight, dark
	- weather_temp_f (Fahrenheit) via Open-Meteo archive API (best-effort)

Deps (Pi)
- python3 -m pip install --user astral requests

Usage
- Ingest only:
	python3 ~/homekit-automation/ingest_enrich.py

- Ingest + enrich:
	python3 ~/homekit-automation/ingest_enrich.py --enrich

- Enrich only:
	python3 ~/homekit-automation/ingest_enrich.py --no-ingest --enrich

- Ingest+enrich lines from stdin (used by event.sh):
	echo "..." | python3 ~/homekit-automation/ingest_enrich.py --enrich --ingest-stdin

- Disable only the optional weather lookup:
	PRESENCE_RELAY_DISABLE_WEATHER=1 python3 ~/homekit-automation/ingest_enrich.py --enrich
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

try:
	import requests
except Exception:
	requests = None

try:
	from astral import Observer
	from astral.sun import sun as sun_times
except Exception:
	Observer = None
	sun_times = None


DEFAULT_BASE = Path.home() / "homekit-automation"
DEFAULT_LOG = DEFAULT_BASE / "automation.log"
DEFAULT_DB = DEFAULT_BASE / "db" / "homekit.sqlite"

PREDAWN_MIN = 60
NOON_WINDOW_MIN = 30
SETTING_MIN = 90
TWILIGHT_MIN = 60
PLACE_RE = re.compile(r"^[a-z0-9_-]+$")


def die(msg: str, code: int = 1) -> None:
	print(msg, file=sys.stderr)
	sys.exit(code)


def sha256_hex(s: str) -> str:
	return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_place(value: Any) -> str:
	if value is None:
		return "unnamed"
	place = str(value).strip().lower()
	if not place:
		return "unnamed"
	if not PLACE_RE.fullmatch(place):
		return "unnamed"
	return place


def derive_place_state(event: Any, place: str, previous_value: Any = None, current_value: Any = None) -> Tuple[str, str]:
	event_s = "" if event is None else str(event).strip().lower()
	previous_place = None if previous_value is None else normalize_place(previous_value)
	current_place = None if current_value is None else normalize_place(current_value)

	if previous_place is None:
		if event_s == "leave":
			previous_place = place
		else:
			previous_place = "unnamed"

	if current_place is None:
		if event_s == "arrive":
			current_place = place
		else:
			current_place = "unnamed"

	return previous_place, current_place


def parse_iso_dt(s: str) -> datetime:
	dt = datetime.fromisoformat(s)
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=timezone.utc)
	return dt


def _offset_str_from_ts(ts_iso: str, dt: datetime) -> str:
	if len(ts_iso) >= 6 and ts_iso[-6] in ("+", "-") and ts_iso[-3] == ":":
		return ts_iso[-6:]
	if ts_iso.endswith("Z"):
		return "+00:00"
	off = dt.strftime("%z")
	if off and len(off) == 5 and off[0] in ("+", "-"):
		return off[:3] + ":" + off[3:]
	return "+00:00"


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
	line = line.rstrip("\n")
	if not line.strip():
		return None

	# Tabs or spaces are fine; split() handles all whitespace.
	toks = line.strip().split()
	if len(toks) < 2:
		return None

	ts_iso = toks[0].strip()
	if not ts_iso:
		return None

	try:
		dt = parse_iso_dt(ts_iso)
	except Exception:
		return None

	out: Dict[str, Any] = {
		"ts_iso": ts_iso,
		"ts_epoch": int(dt.timestamp()),
		"date": dt.date().isoformat(),
		"time": dt.strftime("%H:%M:%S"),
		"offset": _offset_str_from_ts(ts_iso, dt),
		"raw_line": line,
		"raw_sha256": sha256_hex(line),
	}

	kv: Dict[str, str] = {}
	for p in toks[1:]:
		if "=" not in p:
			continue
		k, v = p.split("=", 1)
		kv[k.strip()] = v.strip()

	def to_int_maybe(x: Any) -> Optional[int]:
		if x is None:
			return None
		s = str(x).strip()
		if not s or s == "-":
			return None
		try:
			return int(s)
		except Exception:
			return None

	def to_float_maybe(x: Any) -> Optional[float]:
		if x is None:
			return None
		s = str(x).strip()
		if not s or s == "-":
			return None
		try:
			return float(s)
		except Exception:
			return None

	out["sequence"] = to_int_maybe(kv.get("seq"))
	out["previous_status"] = kv.get("prev")
	out["new_status"] = kv.get("new")
	out["changed"] = to_int_maybe(kv.get("changed"))
	out["event"] = kv.get("event")
	out["place"] = normalize_place(kv.get("place"))
	previous_place, current_place = derive_place_state(
		out["event"],
		out["place"],
		kv.get("previous_place") if "previous_place" in kv else None,
		kv.get("current_place") if "current_place" in kv else None,
	)
	out["previous_place"] = previous_place
	out["current_place"] = current_place
	out["dt_s"] = to_int_maybe(kv.get("dt_s"))
	out["lat"] = to_float_maybe(kv.get("lat"))
	out["lon"] = to_float_maybe(kv.get("lon"))
	out["source"] = kv.get("source")
	out["version"] = to_int_maybe(kv.get("v"))

	return out


def db_connect(db_path: Path) -> sqlite3.Connection:
	db_path.parent.mkdir(parents=True, exist_ok=True)
	conn = sqlite3.connect(str(db_path))
	conn.row_factory = sqlite3.Row
	return conn


def db_init(conn: sqlite3.Connection) -> None:
	# Idempotent; matches your schema.
	conn.execute("""
	CREATE TABLE IF NOT EXISTS events (
		id INTEGER PRIMARY KEY AUTOINCREMENT,

		date TEXT NOT NULL,
		time TEXT NOT NULL,
		offset TEXT NOT NULL,
		sequence INTEGER,
		previous_status TEXT,
		new_status TEXT,
		changed INTEGER,
		event TEXT,
		place TEXT DEFAULT 'unnamed',
		previous_place TEXT DEFAULT 'unnamed',
		current_place TEXT DEFAULT 'unnamed',
		dt_s INTEGER,
		lat REAL,
		lon REAL,
		source TEXT,
		version INTEGER,

		ts_iso TEXT NOT NULL,
		ts_epoch INTEGER NOT NULL,
		raw_line TEXT NOT NULL,
		raw_sha256 TEXT NOT NULL UNIQUE,
		ingested_at_epoch INTEGER NOT NULL,

		is_day INTEGER,
		light_pattern TEXT,
		weather_temp_f REAL
	);
	""")

	cols = {row["name"] for row in conn.execute("PRAGMA table_info(events);").fetchall()}
	if "place" not in cols:
		conn.execute("ALTER TABLE events ADD COLUMN place TEXT DEFAULT 'unnamed';")
	if "previous_place" not in cols:
		conn.execute("ALTER TABLE events ADD COLUMN previous_place TEXT DEFAULT 'unnamed';")
	if "current_place" not in cols:
		conn.execute("ALTER TABLE events ADD COLUMN current_place TEXT DEFAULT 'unnamed';")

	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts_epoch ON events(ts_epoch);")
	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);")
	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_place ON events(place);")
	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_previous_place ON events(previous_place);")
	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_current_place ON events(current_place);")
	conn.execute("CREATE INDEX IF NOT EXISTS idx_events_new_status ON events(new_status);")

	conn.execute("""
	CREATE TABLE IF NOT EXISTS weather_hourly_cache (
		lat_bucket REAL NOT NULL,
		lon_bucket REAL NOT NULL,
		time_iso TEXT NOT NULL,
		temp_c REAL,
		source TEXT,
		fetched_at_epoch INTEGER NOT NULL,
		PRIMARY KEY(lat_bucket, lon_bucket, time_iso)
	);
	""")

	conn.commit()


def ingest_one_line(conn: sqlite3.Connection, line: str) -> Tuple[Optional[int], bool]:
	parsed = parse_log_line(line)
	if not parsed:
		return (None, False)

	now_epoch = int(time.time())

	try:
		cur = conn.execute("""
		INSERT INTO events (
			date, time, offset, sequence, previous_status, new_status, changed, event, place, previous_place, current_place, dt_s,
			lat, lon, source, version,
			ts_iso, ts_epoch,
			raw_line, raw_sha256, ingested_at_epoch
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
		""", (
			parsed["date"],
			parsed["time"],
			parsed["offset"],
			parsed.get("sequence"),
			parsed.get("previous_status"),
			parsed.get("new_status"),
			parsed.get("changed"),
			parsed.get("event"),
			parsed.get("place"),
			parsed.get("previous_place"),
			parsed.get("current_place"),
			parsed.get("dt_s"),
			parsed.get("lat"),
			parsed.get("lon"),
			parsed.get("source"),
			parsed.get("version"),
			parsed["ts_iso"],
			parsed["ts_epoch"],
			parsed["raw_line"],
			parsed["raw_sha256"],
			now_epoch
		))
		conn.commit()
		return (cur.lastrowid, True)
	except sqlite3.IntegrityError:
		return (None, False)


def ingest_log(conn: sqlite3.Connection, log_path: Path, limit: Optional[int] = None) -> Tuple[int, int]:
	if not log_path.exists():
		die(f"log not found: {log_path}")

	inserted = 0
	skipped = 0

	with log_path.open("r", encoding="utf-8", errors="replace") as f:
		for line in f:
			if limit is not None and inserted >= limit:
				break

			_, ok = ingest_one_line(conn, line)
			if ok:
				inserted += 1
			else:
				skipped += 1

	return inserted, skipped


def latlon_bucket(lat: float, lon: float, decimals: int = 3) -> Tuple[float, float]:
	return (round(lat, decimals), round(lon, decimals))


def c_to_f(c: Optional[float]) -> Optional[float]:
	if c is None:
		return None
	try:
		return (float(c) * 9.0 / 5.0) + 32.0
	except Exception:
		return None


def open_meteo_temp_c_hour(conn: sqlite3.Connection, lat: float, lon: float, dt: datetime) -> Optional[float]:
	if os.environ.get("PRESENCE_RELAY_DISABLE_WEATHER") == "1":
		return None

	if requests is None:
		return None

	date_str = dt.date().isoformat()
	hour_key = dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")

	lat_b, lon_b = latlon_bucket(lat, lon)
	row = conn.execute("""
		SELECT temp_c
		FROM weather_hourly_cache
		WHERE lat_bucket=? AND lon_bucket=? AND time_iso=?;
	""", (lat_b, lon_b, hour_key)).fetchone()
	if row is not None:
		return row["temp_c"]

	url = "https://archive-api.open-meteo.com/v1/archive"
	params = {
		"latitude": f"{lat:.6f}",
		"longitude": f"{lon:.6f}",
		"start_date": date_str,
		"end_date": date_str,
		"hourly": "temperature_2m",
		"timezone": "auto",
	}

	try:
		r = requests.get(url, params=params, timeout=12)
		r.raise_for_status()
		data = r.json()
	except Exception:
		return None

	hourly = data.get("hourly") or {}
	times = hourly.get("time") or []
	t2m = hourly.get("temperature_2m") or []

	try:
		idx = times.index(hour_key)
	except Exception:
		return None

	try:
		temp_c = float(t2m[idx])
	except Exception:
		temp_c = None

	conn.execute("""
		INSERT OR REPLACE INTO weather_hourly_cache (
			lat_bucket, lon_bucket, time_iso, temp_c, source, fetched_at_epoch
		) VALUES (?, ?, ?, ?, ?, ?);
	""", (
		lat_b, lon_b, hour_key,
		temp_c,
		"open-meteo-archive",
		int(time.time())
	))
	conn.commit()

	return temp_c


def classify_light_pattern(dt: datetime, sunrise: datetime, sunset: datetime, solar_noon: datetime) -> str:
	predawn_start = sunrise - timedelta(minutes=PREDAWN_MIN)
	noon_start = solar_noon - timedelta(minutes=NOON_WINDOW_MIN)
	noon_end = solar_noon + timedelta(minutes=NOON_WINDOW_MIN)
	setting_start = sunset - timedelta(minutes=SETTING_MIN)
	twilight_end = sunset + timedelta(minutes=TWILIGHT_MIN)

	if dt >= predawn_start and dt < sunrise:
		return "pre-dawn"

	if dt >= sunrise and dt < noon_start:
		return "rising"

	if dt >= noon_start and dt <= noon_end:
		return "noon"

	if dt > noon_end and dt < setting_start:
		return "afternoon"

	if dt >= setting_start and dt < sunset:
		return "setting"

	if dt >= sunset and dt <= twilight_end:
		return "twilight"

	return "dark"


def compute_sun_small(lat: float, lon: float, dt: datetime) -> Optional[Dict[str, Any]]:
	if Observer is None or sun_times is None:
		return None

	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=timezone.utc)

	obs = Observer(latitude=lat, longitude=lon, elevation=0)
	tz = dt.tzinfo

	try:
		s = sun_times(obs, date=dt.date(), tzinfo=tz)
	except Exception:
		return None

	sunrise = s.get("sunrise")
	sunset = s.get("sunset")

	solar_noon = s.get("noon") or s.get("transit")
	if solar_noon is None and sunrise is not None and sunset is not None:
		try:
			solar_noon = sunrise + (sunset - sunrise) / 2
		except Exception:
			solar_noon = None

	if sunrise is None or sunset is None or solar_noon is None:
		return None

	is_day = 1 if (dt >= sunrise and dt <= sunset) else 0
	light_pattern = classify_light_pattern(dt, sunrise, sunset, solar_noon)

	return {
		"is_day": is_day,
		"light_pattern": light_pattern,
	}


def enrich_event_id(conn: sqlite3.Connection, event_id: int) -> bool:
	row = conn.execute("""
	SELECT id, ts_iso, lat, lon, is_day, light_pattern, weather_temp_f
	FROM events
	WHERE id=?;
	""", (event_id,)).fetchone()
	if row is None:
		return False

	if row["lat"] is None or row["lon"] is None:
		return False

	need = (row["is_day"] is None) or (row["light_pattern"] is None) or (row["weather_temp_f"] is None)
	if not need:
		return True

	try:
		dt = parse_iso_dt(row["ts_iso"])
	except Exception:
		return False

	lat = float(row["lat"])
	lon = float(row["lon"])

	sun = compute_sun_small(lat, lon, dt)
	temp_c = open_meteo_temp_c_hour(conn, lat, lon, dt)
	temp_f = c_to_f(temp_c)

	conn.execute("""
	UPDATE events SET
		is_day=COALESCE(?, is_day),
		light_pattern=COALESCE(?, light_pattern),
		weather_temp_f=COALESCE(?, weather_temp_f)
	WHERE id=?;
	""", (
		(sun or {}).get("is_day"),
		(sun or {}).get("light_pattern"),
		temp_f,
		event_id
	))
	conn.commit()
	return True


def enrich_events(conn: sqlite3.Connection, limit: Optional[int] = None) -> Tuple[int, int]:
	q = """
	SELECT id
	FROM events
	WHERE lat IS NOT NULL
	AND lon IS NOT NULL
	AND (
		is_day IS NULL
		OR light_pattern IS NULL
		OR weather_temp_f IS NULL
	)
	ORDER BY ts_epoch ASC
	"""
	if limit is not None:
		q += f" LIMIT {int(limit)}"

	rows = conn.execute(q).fetchall()
	done = 0
	skipped = 0

	for r in rows:
		if enrich_event_id(conn, int(r["id"])):
			done += 1
		else:
			skipped += 1

	return done, skipped


def print_summary(conn: sqlite3.Connection) -> None:
	n = conn.execute("SELECT COUNT(*) AS n FROM events;").fetchone()["n"]
	n_full = conn.execute("""
		SELECT COUNT(*) AS n
		FROM events
		WHERE is_day IS NOT NULL
		AND light_pattern IS NOT NULL
		AND weather_temp_f IS NOT NULL;
	""").fetchone()["n"]
	n_missing = conn.execute("""
		SELECT COUNT(*) AS n
		FROM events
		WHERE lat IS NOT NULL AND lon IS NOT NULL
		AND (is_day IS NULL OR light_pattern IS NULL OR weather_temp_f IS NULL);
	""").fetchone()["n"]

	print(f"events: {n}")
	print(f"enriched (all 3 present): {n_full}")
	print(f"enrich-missing (with lat/lon): {n_missing}")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--log", default=str(DEFAULT_LOG))
	ap.add_argument("--db", default=str(DEFAULT_DB))
	ap.add_argument("--enrich", action="store_true")
	ap.add_argument("--no-ingest", action="store_true")
	ap.add_argument("--ingest-stdin", action="store_true")
	ap.add_argument("--ingest-limit", type=int, default=None)
	ap.add_argument("--enrich-limit", type=int, default=None)
	ap.add_argument("--quiet", action="store_true")
	args = ap.parse_args()

	log_path = Path(args.log).expanduser()
	db_path = Path(args.db).expanduser()

	conn = db_connect(db_path)
	db_init(conn)

	if args.ingest_stdin:
		text = sys.stdin.read()
		lines = [ln for ln in text.splitlines() if ln.strip()]
		inserted_ids: List[int] = []

		for ln in lines:
			event_id, ok = ingest_one_line(conn, ln)
			if ok and event_id is not None:
				inserted_ids.append(int(event_id))

		if args.enrich and inserted_ids:
			for eid in inserted_ids:
				enrich_event_id(conn, eid)

		if not args.quiet:
			print(f"ingest-stdin: lines={len(lines)} inserted={len(inserted_ids)}")
			if args.enrich:
				print(f"enrich-stdin: attempted={len(inserted_ids)}")

	else:
		if not args.no_ingest:
			ins, skip = ingest_log(conn, log_path, limit=args.ingest_limit)
			if not args.quiet:
				print(f"ingest: inserted={ins} skipped(existing/bad)={skip}")

		if args.enrich:
			if Observer is None and not args.quiet:
				print("enrich: astral not available (is_day/light_pattern will be NULL). Install: python3 -m pip install --user astral", file=sys.stderr)
			if requests is None and not args.quiet:
				print("enrich: requests not available (weather_temp_f will be NULL). Install: python3 -m pip install --user requests", file=sys.stderr)

			done, skip = enrich_events(conn, limit=args.enrich_limit)
			if not args.quiet:
				print(f"enrich: updated={done} skipped(bad ts/coords)={skip}")

		if not args.quiet:
			print_summary(conn)


if __name__ == "__main__":
	main()
