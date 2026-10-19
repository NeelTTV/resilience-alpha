"""Train novelty detection from observed normal HTTP windows, with a held-out split."""

import hashlib
import json
import math
import os
import time
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

FEATURES = ["log_request_rate", "error_ratio", "mean_latency", "unauthorized_ratio"]
WINDOW = 3.0


def quarantine_candidate(events, protected, infrastructure):
    counts = Counter(e["client_ip"] for e in events if e["client_ip"] != "internal")
    if not counts:
        return None
    highest = max(counts.values())
    dominant = [source for source, count in counts.items() if count == highest]
    # Minimum evidence is an action-safety guard, not the anomaly classifier.
    if highest < 12 or len(dominant) != 1 or dominant[0] in set(protected) | set(infrastructure):
        return None
    return dominant[0]


def vector(events, seconds=WINDOW):
    if not events:
        return [0.0] * len(FEATURES)
    return [
        math.log1p(len(events) / seconds),
        sum(e["status"] >= 400 for e in events) / len(events),
        sum(e["duration"] for e in events) / len(events),
        sum(e["status"] == 401 for e in events) / len(events),
    ]


def train(db, start, end, output=None):
    rows = db.execute(
        "SELECT * FROM events WHERE service='payment' AND route='/transactions' "
        "AND timestamp>=? AND timestamp<? ORDER BY timestamp",
        (start, end),
    ).fetchall()
    windows = []
    for timestamp in np.arange(start, end - WINDOW + 0.01, WINDOW):
        events = [e for e in rows if timestamp <= e["timestamp"] < timestamp + WINDOW]
        if events:
            # Training is aggregated by source, exactly like inference.
            for source in sorted({e["client_ip"] for e in events} - {"internal"}):
                source_events = [e for e in events if e["client_ip"] == source]
                windows.append(
                    {"at": float(timestamp), "source": source, "features": vector(source_events)}
                )
    if len(windows) < 16:
        raise ValueError("Need at least 16 observed 3-second normal windows; collect more traffic")
    split = max(12, int(len(windows) * 0.75))
    train_x = [w["features"] for w in windows[:split]]
    valid_x = [w["features"] for w in windows[split:]]
    # Preserve physical feature scales: tiny normal latency variance must not dominate distance.
    model = make_pipeline(StandardScaler(with_std=False), OneClassSVM(nu=0.05, gamma="auto"))
    model.fit(train_x)
    # Calibrate a conservative novelty boundary using ONLY normal validation windows.
    scores = model.decision_function(valid_x)
    threshold = float(min(-0.03, np.min(scores) - 0.05))
    dataset = json.dumps(windows, sort_keys=True).encode()
    metadata = {
        "version": hashlib.sha256(dataset + b"|center-only|nu=.05|gamma=auto|v2").hexdigest()[:16],
        "algorithm": "OneClassSVM-RBF",
        "preprocessing": "center_only; no division by low-variance latency standard deviation",
        "hyperparameters": {"nu": 0.05, "gamma": "auto"},
        "features": FEATURES,
        "window_seconds": WINDOW,
        "threshold": threshold,
        "trained_at": time.time(),
        "start": start,
        "end": end,
        "train_windows": len(train_x),
        "validation_windows": len(valid_x),
        "validation_false_positives": int(np.sum(scores < threshold)),
        "provenance": "HTTP metadata collected from this lab; normal traffic only",
        "protected_sources": sorted({window["source"] for window in windows}),
        "limitations": "Small lab dataset. Calibration split is not an independent final test.",
    }
    directory = Path(output or os.getenv("MODEL_DIR", "/state/model"))
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, directory / "model.tmp")
    (directory / "model.tmp").replace(directory / "model.joblib")
    (directory / "training-windows.json").write_bytes(dataset)
    metadata["artifact_sha256"] = hashlib.sha256(
        (directory / "model.joblib").read_bytes()
    ).hexdigest()
    (directory / "metadata.tmp").write_text(json.dumps(metadata, indent=2))
    (directory / "metadata.tmp").replace(directory / "metadata.json")
    return metadata


def load(directory=None):
    path = Path(directory or os.getenv("MODEL_DIR", "/state/model"))
    metadata = json.loads((path / "metadata.json").read_text())
    if "protected_sources" not in metadata:
        windows = json.loads((path / "training-windows.json").read_text())
        metadata["protected_sources"] = sorted({window["source"] for window in windows})
    if (
        hashlib.sha256((path / "model.joblib").read_bytes()).hexdigest()
        != metadata["artifact_sha256"]
    ):
        raise ValueError("Model artifact checksum mismatch")
    # Trusted, self-generated artifact. This directory is writable ONLY by the supervisor.
    return joblib.load(path / "model.joblib"), metadata
