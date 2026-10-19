"""Fresh held-out normal traffic AFTER the frozen model's recovery exercise."""

import json
import random
import subprocess
import sys
import time

from smoke import ROOT, request

if __name__ == "__main__":
    token = request(
        "/auth/token",
        {"username": "operator", "password": (ROOT / ".secrets/demo_password").read_text().strip()},
    )["access_token"]
    headers = {"Authorization": "Bearer " + token}
    randomizer = random.Random(7319)
    start = time.time()
    print(
        "Collecting 45 seconds of fresh authenticated normal traffic (no retraining).", flush=True
    )
    while time.time() - start < 45:
        request("/api/transactions", headers=headers)
        time.sleep(randomizer.choice([0.2, 0.5, 1.0, 1.5]))
    end = time.time()
    time.sleep(2)
    subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_model.py",
            "--normal-start",
            str(start),
            "--normal-end",
            str(end),
        ],
        cwd=ROOT,
        check=True,
    )
    evaluation = json.loads((ROOT / "output/evidence/model-evaluation.json").read_text())
    if evaluation["false_positive_on_assumed_quiet"] or evaluation["false_negative"]:
        raise SystemExit("Confirmation found classification errors; inspect evaluation")
