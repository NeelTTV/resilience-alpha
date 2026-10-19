"""Back up the fictitious DB and restore to a NEW isolated database; never overwrite live data."""

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*args, data=None):
    return subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            *args,
        ],
        cwd=ROOT,
        input=data,
    )


def fingerprint(database):
    content = command(
        "psql",
        "-U",
        "resilience",
        "-d",
        database,
        "-At",
        "-c",
        "SELECT row_to_json(t) FROM transactions t ORDER BY id",
    )
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "transactions": len(content.splitlines()),
    }


if __name__ == "__main__":
    started = time.time()
    backup = command("pg_dump", "-U", "resilience", "-d", "resilience", "-Fc")
    directory = ROOT / "data/backups"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + ".dump")
    path.write_bytes(backup)
    temporary_database = "restorecheck_" + uuid.uuid4().hex
    command("createdb", "-U", "resilience", temporary_database)
    try:
        restore_started = time.time()
        command(
            "pg_restore",
            "-U",
            "resilience",
            "--no-owner",
            "--exit-on-error",
            "-d",
            temporary_database,
            data=backup,
        )
        restored = fingerprint(temporary_database)
        live = fingerprint("resilience")
        result = {
            "backup": str(path.relative_to(ROOT)),
            "restored": restored,
            "live": live,
            "restore_seconds": round(time.time() - restore_started, 3),
            "total_seconds": round(time.time() - started, 3),
            "passed": restored == live,
            "scope": "restore into fresh local database; no host-loss recovery proven",
        }
        evidence = ROOT / "output/evidence/backup.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(
                "Differences found (possibly concurrent writes); rerun during an idle window"
            )
    finally:
        if not temporary_database.startswith("restorecheck_"):
            raise RuntimeError("Unexpected restore target")
        command("dropdb", "-U", "resilience", temporary_database)
