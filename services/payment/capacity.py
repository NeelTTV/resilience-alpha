"""Finite shared admission budget for the bounded application-DoS lab scenario.

This models a shared resource quota, not a vulnerability in a payment provider.
The anomaly detector is independent of this fixed capacity guard.
"""

import ipaddress
import json
import os
import threading
import time
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

from services.common.telemetry import record


class Budget:
    def __init__(self, rate=20.0, burst=20.0):
        self.rate, self.burst = rate, burst
        self.tokens = burst
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def admit(self):
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens < 1:
                return False
            self.tokens -= 1
            return True


budget = Budget(float(os.getenv("CAPACITY_RPS", "20")), 20)


def source_ip(request: Request):
    # Nginx overwrites this header using the trusted WAF's X-Real-IP.
    raw = request.headers.get("x-lab-client-ip", "internal")
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return "internal"


def blocked(ip: str):
    path = Path(os.getenv("POLICY_FILE", "/policy/blocks.json"))
    if not path.exists():
        return False
    # Fail closed on unreadable/malformed policy rather than silently disabling quarantine.
    rules = json.loads(path.read_text())
    return any(r["ip"] == ip and r["expires_at"] > time.time() for r in rules)


async def admission(request: Request, call_next):
    if request.url.path != "/transactions" or os.getenv("LAB_CAPACITY_ENABLED", "false") != "true":
        return await call_next(request)
    ip = source_ip(request)
    start = time.perf_counter()
    try:
        denied = blocked(ip)
    except (OSError, ValueError, KeyError, TypeError):
        denied = True
    status = 403 if denied else (None if budget.admit() else 503)
    if status:
        record("payment", request, "/transactions", status, time.perf_counter() - start)
        return JSONResponse(
            {"detail": "Source quarantined" if status == 403 else "Shared capacity exhausted"},
            status_code=status,
            headers={"Retry-After": "2"},
        )
    return await call_next(request)
