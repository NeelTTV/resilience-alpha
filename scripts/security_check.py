"""Read-only security checks against this local lab's WAF and TLS listener."""

import json
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from smoke import BASE, ROOT


def status(path, **kwargs):
    try:
        with urlopen(Request(BASE + path, **kwargs), timeout=10) as response:
            return response.status
    except HTTPError as error:
        return error.code


if __name__ == "__main__":
    results = {
        "unauthenticated_payment_denied": status("/api/transactions") == 401,
        "internal_api_not_published": status("/api/metrics") == 404,
        "internal_control_not_published": status("/control/quarantine") == 404,
        "waf_blocks_sql_injection_probe": status("/api/health?probe=%27%20OR%201%3D1--") == 403,
    }
    context = ssl.create_default_context(cafile=str(ROOT / ".secrets/tls_cert"))
    with urlopen("https://127.0.0.1:8443/api/health", context=context, timeout=10) as response:
        results["tls_certificate_and_hostname_verified"] = response.status == 200
    path = ROOT / "output/evidence/security.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    if not all(results.values()):
        raise SystemExit("Security check failed")
