"""Bounded request-flood exercise, restricted to one explicitly named private lab host.

No redirects, no credentials, no scanning, <=100 rps, <=60 seconds, <=8 in-flight requests.
"""

import argparse
import collections
import concurrent.futures
import ipaddress
import json
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate_target(target, approved_host):
    parsed = urlsplit(target)
    if parsed.scheme != "http" or parsed.hostname != approved_host:
        raise ValueError("Use http and the exact explicitly approved lab host")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Target must be a base URL without credentials, path or query")
    addresses = {r[4][0] for r in socket.getaddrinfo(parsed.hostname, parsed.port or 80)}
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if not (
            ip.is_private
            and not ip.is_loopback
            and not ip.is_link_local
            and not ip.is_unspecified
            and not ip.is_multicast
        ):
            raise ValueError("Only an isolated private lab address is permitted")
    return target.rstrip("/")


def run(target, duration, rps):
    statuses = collections.Counter()
    lock = threading.Lock()
    slots = threading.BoundedSemaphore(8)

    def send():
        try:
            # Explicitly disable environment proxies and redirects.
            from urllib.request import ProxyHandler

            opener = build_opener(ProxyHandler({}), NoRedirect())
            try:
                with opener.open(Request(target + "/api/transactions"), timeout=2) as response:
                    status = response.status
            except HTTPError as exc:
                status = exc.code
            except (URLError, TimeoutError, OSError):
                status = "network_error"
            with lock:
                statuses[str(status)] += 1
        finally:
            slots.release()

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for index in range(duration * rps):
            delay = start + index / rps - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            if time.monotonic() - start >= duration:
                break
            if slots.acquire(blocking=False):
                pool.submit(send)
    return {
        "duration_seconds": round(time.monotonic() - start, 2),
        "requested_rps": rps,
        "statuses": dict(statuses),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--lab-host", required=True, help="Exact approved PC Hôte hostname/IP")
    parser.add_argument("--seconds", type=int, default=30, choices=range(1, 61))
    parser.add_argument("--rps", type=int, default=60, choices=range(1, 101))
    args = parser.parse_args()
    target = validate_target(args.target, args.lab_host)
    print(json.dumps(run(target, args.seconds, args.rps)), flush=True)
