#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from http.server import ThreadingHTTPServer
from pathlib import Path


def die(message: str, code: int = 1) -> None:
	print(message, file=sys.stderr)
	sys.exit(code)


def load_module(name: str, path: Path):
	spec = importlib.util.spec_from_file_location(name, path)
	if spec is None or spec.loader is None:
		die(f"unable to load module: {name}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def require_inside(child: Path, parent: Path) -> Path:
	child_r = child.resolve()
	parent_r = parent.resolve()
	try:
		child_r.relative_to(parent_r)
	except ValueError:
		die("refusing to operate outside demo state")
	return child_r


def clean(repo_root: Path, tmp_dir: Path) -> None:
	expected = repo_root / "demo" / "tmp"
	tmp_r = require_inside(tmp_dir, expected)
	if tmp_r != expected.resolve():
		die("refusing to clean unexpected path")

	tmp_r.mkdir(parents=True, exist_ok=True)
	for child in tmp_r.iterdir():
		if child.is_dir() and not child.is_symlink():
			shutil.rmtree(child)
		else:
			child.unlink()


def serve(repo_root: Path, ready_file: Path) -> None:
	webhookd = load_module("presence_relay_webhookd", repo_root / "app" / "webhookd.py")
	webhookd.init_db()
	httpd = ThreadingHTTPServer((webhookd.LISTEN_HOST, webhookd.LISTEN_PORT), webhookd.Handler)
	ready_file.parent.mkdir(parents=True, exist_ok=True)
	ready_file.write_text("ready\n", encoding="utf-8")
	httpd.serve_forever()


def row_payload(row: sqlite3.Row) -> dict:
	try:
		payload = json.loads(row["raw_json"] or "{}")
	except json.JSONDecodeError:
		payload = {}

	return {
		"event": payload.get("event", row["event"]),
		"place": payload.get("place", row["place"] or "unnamed"),
		"lat": payload.get("lat", row["lat"]),
		"lon": payload.get("lon", row["lon"]),
		"ts": payload.get("ts", ""),
	}


def deliver(queue_db: Path, demo_home: Path, event_sh: Path, adapter_log: Path) -> None:
	conn = sqlite3.connect(str(queue_db))
	conn.row_factory = sqlite3.Row
	try:
		rows = conn.execute("""
			SELECT *
			FROM queue
			WHERE delivered_at_epoch IS NULL
			ORDER BY id ASC;
		""").fetchall()

		env = os.environ.copy()
		env["HOME"] = str(demo_home)
		adapter_log.parent.mkdir(parents=True, exist_ok=True)

		with adapter_log.open("a", encoding="utf-8") as log:
			for row in rows:
				payload = row_payload(row)
				cmd = [
					"bash",
					str(event_sh),
					str(payload["event"]),
					str(payload["place"]),
					"" if payload["lat"] is None else str(payload["lat"]),
					"" if payload["lon"] is None else str(payload["lon"]),
					"" if payload["ts"] is None else str(payload["ts"]),
				]
				subprocess.run(cmd, env=env, stdout=log, stderr=log, text=True, check=True)
				conn.execute(
					"UPDATE queue SET delivered_at_epoch = ? WHERE id = ?;",
					(int(time.time()), row["id"]),
				)
			conn.commit()
	finally:
		conn.close()


def viewer_check(repo_root: Path, db_path: Path) -> None:
	os.environ["COMEANDGO_DB"] = str(db_path)
	viewer = load_module(
		"presence_relay_viewer",
		repo_root / "nodes/home-lan-target/homekit-automation/web/assets/python/server.py",
	)
	events = viewer.fetch_events(10)
	if len(events) != 2:
		die("viewer reader did not return the expected event count")
	required = {"event", "place", "previous_place", "current_place", "sequence"}
	for event in events:
		if not required.issubset(event.keys()):
			die("viewer reader returned an unexpected event shape")
	print("viewer: existing server reader fetched 2 rows")


def verify(db_path: Path) -> None:
	conn = sqlite3.connect(str(db_path))
	conn.row_factory = sqlite3.Row
	try:
		rows = conn.execute("""
			SELECT sequence, event, place, previous_place, current_place
			FROM events
			ORDER BY ts_epoch ASC, sequence ASC;
		""").fetchall()
	finally:
		conn.close()

	expected = [
		(1, "leave", "sheridan-plaza", "sheridan-plaza", "unnamed"),
		(2, "arrive", "kilmer-elementary", "unnamed", "kilmer-elementary"),
	]
	got = [
		(row["sequence"], row["event"], row["place"], row["previous_place"], row["current_place"])
		for row in rows
	]
	if got != expected:
		die("persisted rows did not match expected place transitions")


def stop_pid(pid_file: Path) -> None:
	if not pid_file.exists():
		return
	try:
		pid = int(pid_file.read_text(encoding="utf-8").strip())
	except Exception:
		pid_file.unlink(missing_ok=True)
		return

	try:
		os.kill(pid, signal.SIGTERM)
	except ProcessLookupError:
		pass
	for _ in range(50):
		try:
			os.kill(pid, 0)
		except ProcessLookupError:
			break
		time.sleep(0.1)
	else:
		try:
			os.kill(pid, signal.SIGKILL)
		except ProcessLookupError:
			pass
	pid_file.unlink(missing_ok=True)


def main() -> None:
	if len(sys.argv) < 2:
		die("usage: local_demo.py clean|serve|deliver|viewer-check|verify|stop ...", 2)

	cmd = sys.argv[1]
	if cmd == "clean":
		if len(sys.argv) != 4:
			die("usage: local_demo.py clean <repo_root> <tmp_dir>", 2)
		clean(Path(sys.argv[2]), Path(sys.argv[3]))
	elif cmd == "serve":
		if len(sys.argv) != 4:
			die("usage: local_demo.py serve <repo_root> <ready_file>", 2)
		serve(Path(sys.argv[2]), Path(sys.argv[3]))
	elif cmd == "deliver":
		if len(sys.argv) != 6:
			die("usage: local_demo.py deliver <queue_db> <demo_home> <event_sh> <adapter_log>", 2)
		deliver(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
	elif cmd == "viewer-check":
		if len(sys.argv) != 4:
			die("usage: local_demo.py viewer-check <repo_root> <db_path>", 2)
		viewer_check(Path(sys.argv[2]), Path(sys.argv[3]))
	elif cmd == "verify":
		if len(sys.argv) != 3:
			die("usage: local_demo.py verify <db_path>", 2)
		verify(Path(sys.argv[2]))
	elif cmd == "stop":
		if len(sys.argv) != 3:
			die("usage: local_demo.py stop <pid_file>", 2)
		stop_pid(Path(sys.argv[2]))
	else:
		die(f"unknown command: {cmd}", 2)


if __name__ == "__main__":
	main()
