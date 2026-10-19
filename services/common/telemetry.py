import json
import logging
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request duration", ["service", "route"])
logger = logging.getLogger("uvicorn.error")


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
                REQUESTS.labels(service, request.method, route, str(status)).inc()
                LATENCY.labels(service, route).observe(elapsed)
                logger.info(json.dumps({
                    "service": service, "method": request.method, "route": route,
                    "status": status, "duration_seconds": round(elapsed, 6),
                }))

