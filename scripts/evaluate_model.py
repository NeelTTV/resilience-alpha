"""Evaluate the frozen model on the held-out exercise and subsequent quiet traffic."""

import argparse
import json
import subprocess
import time
from pathlib import Path


def evaluate(source, normal_start=None, normal_end=None):
    from services.supervisor.model import WINDOW, load, vector
    from services.supervisor.store import connect

    model, metadata = load()
    with connect() as db:
        attack = db.execute(
            "SELECT * FROM events WHERE service='payment' AND route='/transactions' "
            "AND client_ip=? ORDER BY timestamp",
            (source,),
        ).fetchall()
        if not attack:
            raise ValueError("No observations for this exercise source")
        quiet_start = normal_start or attack[-1]["timestamp"] + 5
        quiet = db.execute(
            "SELECT * FROM events WHERE service='payment' AND route='/transactions' "
            "AND timestamp>=? AND timestamp<? AND client_ip!='internal' ORDER BY timestamp",
            (quiet_start, normal_end or time.time()),
        ).fetchall()

    def windows(rows):
        groups = {}
        for row in rows:
            key = (int(row["timestamp"] // WINDOW), row["client_ip"])
            groups.setdefault(key, []).append(row)
        return list(groups.values())

    attack_windows, quiet_windows = windows(attack), windows(quiet)
    scores_attack = model.decision_function([vector(w) for w in attack_windows])
    scores_quiet = (
        model.decision_function([vector(w) for w in quiet_windows]) if quiet_windows else []
    )
    tp = sum(float(score) < metadata["threshold"] for score in scores_attack)
    fp = sum(float(score) < metadata["threshold"] for score in scores_quiet)
    return {
        "model_version": metadata["version"],
        "model_frozen_before_exercise": metadata["trained_at"] < attack[0]["timestamp"],
        "attack_source": source,
        "attack_windows": len(attack_windows),
        "quiet_windows": len(quiet_windows),
        "true_positive": tp,
        "false_negative": len(attack_windows) - tp,
        "false_positive_on_assumed_quiet": fp,
        "true_negative": len(quiet_windows) - fp,
        "recall_on_exercise": tp / len(attack_windows),
        "quiet_start": quiet_start,
        "quiet_samples": [
            {"features": vector(window), "score": float(score)}
            for window, score in zip(quiet_windows, scores_quiet)
        ],
        "attack_samples": [
            {"features": vector(window), "score": float(score)}
            for window, score in zip(attack_windows, scores_attack)
        ],
        "limitations": "Small correlated lab windows; quiet period assumed normal. "
        "Attack windows include quarantined requests. No production generalization.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--normal-start", type=float)
    parser.add_argument("--normal-end", type=float)
    args = parser.parse_args()
    if args.inside:
        print(json.dumps(evaluate(args.source, args.normal_start, args.normal_end), indent=2))
    else:
        root = Path(__file__).resolve().parents[1]
        recovery = json.loads((root / "output/evidence/recovery.json").read_text())
        command = [
            "docker",
            "compose",
            "exec",
            "-T",
            "supervisor",
            "python",
            "-",
            "--inside",
            "--source",
            recovery["attacker_ip"],
        ]
        if args.normal_start is not None:
            command.extend(
                ["--normal-start", str(args.normal_start), "--normal-end", str(args.normal_end)]
            )
        result = subprocess.check_output(command, input=Path(__file__).read_bytes(), cwd=root)
        (root / "output/evidence/model-evaluation.json").write_bytes(result)
        print(result.decode())
