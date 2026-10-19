"""Collect actual normal HTTP observations and train inside the supervisor container."""

import argparse
import json
import random
import subprocess
import time

from smoke import BASE, ROOT, request

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=75, choices=range(60, 301))
    args = parser.parse_args()
    token = request(
        "/auth/token",
        {"username": "operator", "password": (ROOT / ".secrets/demo_password").read_text().strip()},
    )["access_token"]
    headers = {"Authorization": "Bearer " + token}
    rng = random.Random(2026)
    start = time.time()
    calls = 0
    print(f"Collecting normal traffic on {BASE} for {args.seconds}s", flush=True)
    while time.time() - start < args.seconds:
        rate = rng.choice([0.5, 1, 2, 4, 7])
        window_end = min(start + args.seconds, time.time() + 3)
        while time.time() < window_end:
            request("/api/transactions", headers=headers)
            calls += 1
            time.sleep(1 / rate)
    end = time.time()
    time.sleep(2)  # Let the file collector ingest the final completed window.
    result = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "supervisor",
            "python",
            "-m",
            "services.supervisor.train",
            "--start",
            str(start),
            "--end",
            str(end),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    metadata = json.loads(result.stdout)
    directory = ROOT / "output/evidence"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "calibration.json").write_text(
        json.dumps(
            {
                "requests": calls,
                "model": metadata,
            },
            indent=2,
        )
    )
    print(json.dumps(metadata, indent=2))
