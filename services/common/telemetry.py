import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request duration", ["service", "route"])
logger = logging.getLogger("uvicorn.error")
file_loggers = {}


def record(service: str, request: Request, route: str, status: int, elapsed: float):
    REQUESTS.labels(service, request.method, route, str(status)).inc()
    LATENCY.labels(service, route).observe(elapsed)
    event = {
        "timestamp": time.time(),
        "service": service,
        "method": request.method,
        "route": route,
        "status": status,
        "duration_seconds": round(elapsed, 6),
        "client_ip": request.headers.get("x-lab-client-ip", "internal")[:64],
    }
    message = json.dumps(event)
    logger.info(message)
    if os.getenv("LOG_DIR"):
        if service not in file_loggers:
            path = Path(os.environ["LOG_DIR"])
            path.mkdir(parents=True, exist_ok=True)
            file_logger = logging.getLogger("audit." + service)
            handler = RotatingFileHandler(
                path / (service + ".jsonl"),
                maxBytes=5_000_000,
                backupCount=3,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            file_logger.addHandler(handler)
            file_logger.setLevel(logging.INFO)
            file_logger.propagate = False
            file_loggers[service] = file_logger
        file_loggers[service].info(message)


def instrument(app: FastAPI, service: str):
    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})

    @app.middleware("http")
    async def observe(request: Request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = getattr(request.scope.get("route"), "path", "unmatched")
            if route != "/metrics":
                record(service, request, route, status, elapsed)
