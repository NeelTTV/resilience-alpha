import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect():
    path = Path(os.getenv("SUPERVISOR_STATE", "/state"))
    path.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path / "supervisor.db", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, timestamp REAL, service TEXT, client_ip TEXT,
            status INTEGER, duration REAL, route TEXT);
        CREATE INDEX IF NOT EXISTS events_time ON events(timestamp);
        CREATE TABLE IF NOT EXISTS cursors (path TEXT PRIMARY KEY, inode TEXT, offset INTEGER);
        CREATE TABLE IF NOT EXISTS checkpoints (name TEXT PRIMARY KEY, value INTEGER);
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY, source_ip TEXT, state TEXT, created_at REAL,
            updated_at REAL, payload TEXT);
        CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY, incident_id TEXT, timestamp REAL, state TEXT, detail TEXT);
    """)
    try:
        yield db
    finally:
        db.close()


def ingest(db, logs=None):
    count = 0
    for path in Path(logs or os.getenv("LOG_DIR", "/logs")).glob("*.jsonl"):
        stat = path.stat()
        inode = str(stat.st_ino)
        cursor = db.execute("SELECT * FROM cursors WHERE path=?", (str(path),)).fetchone()
        offset = cursor["offset"] if cursor and cursor["inode"] == inode else 0
        if offset > stat.st_size:
            offset = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            for _ in range(10000):
                line_start = stream.tell()
                line = stream.readline()
                if not line:
                    break
                if not line.endswith(b"\n"):
                    stream.seek(line_start)
                    break
                try:
                    event = json.loads(line)
                    timestamp = float(event["timestamp"])
                    # Keep request metadata only, never raw headers or request bodies.
                    db.execute(
                        "INSERT INTO events(timestamp,service,client_ip,status,duration,route) "
                        "VALUES(?,?,?,?,?,?)",
                        (
                            timestamp,
                            event["service"],
                            event.get("client_ip", "internal"),
                            int(event["status"]),
                            float(event.get("duration_seconds", 0)),
                            event.get("route", "unmatched")[:128],
                        ),
                    )
                    count += 1
                except (ValueError, KeyError, TypeError):
                    continue
            db.execute(
                "INSERT OR REPLACE INTO cursors VALUES(?,?,?)",
                (
                    str(path),
                    inode,
                    stream.tell(),
                ),
            )
    db.execute("DELETE FROM events WHERE timestamp < ?", (time.time() - 86400,))
    db.commit()
    return count


def transition(db, incident_id, state, detail):
    now = time.time()
    db.execute("UPDATE incidents SET state=?, updated_at=? WHERE id=?", (state, now, incident_id))
    db.execute(
        "INSERT INTO timeline(incident_id,timestamp,state,detail) VALUES(?,?,?,?)",
        (
            incident_id,
            now,
            state,
            json.dumps(detail),
        ),
    )
    db.commit()


def incidents(db):
    rows = db.execute("SELECT * FROM incidents ORDER BY created_at DESC LIMIT 50").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("payload"))
        item["timeline"] = [
            {**dict(event), "detail": json.loads(event["detail"])}
            for event in db.execute(
                "SELECT timestamp,state,detail FROM timeline WHERE incident_id=? ORDER BY id",
                (row["id"],),
            )
        ]
        result.append(item)
    return result
