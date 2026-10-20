"""Generate ignored firmware config locally; never output Wi-Fi or device secrets."""

import getpass
import json
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).resolve().parents[1]


def configure():
    ssid = input("SSID exact du hotspot RESILIENCE-G<n> : ").strip()
    if not ssid.startswith("RESILIENCE-G") or not ssid[12:].isdigit():
        raise SystemExit("Indiquez le SSID avec votre numéro de groupe réel.")
    password = getpass.getpass("Mot de passe Wi-Fi (saisie masquée) : ")
    url = input("URL HTTPS du module [https://192.168.137.1:8443/auth/device/status] : ").strip()
    url = url or "https://192.168.137.1:8443/auth/device/status"
    if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
        raise SystemExit("Une URL HTTPS est requise.")
    cert = x509.load_pem_x509_certificate((ROOT / ".secrets/tls_cert").read_bytes())
    fingerprint = cert.fingerprint(hashes.SHA1()).hex(" ").upper()
    values = {
        "WIFI_SSID": ssid,
        "WIFI_PASSWORD": password,
        "STATUS_URL": url,
        "DEVICE_KEY": (ROOT / ".secrets/device_key").read_text().strip(),
        "TLS_FINGERPRINT": fingerprint,
    }
    target = ROOT / "infra/esp8266/include/lab_config.h"
    target.write_text(
        "#pragma once\n"
        + "\n".join(f"#define {name} {json.dumps(value)}" for name, value in values.items())
        + "\n#define GREEN_PIN 5\n#define RED_PIN 4\n",
        encoding="utf-8",
    )
    print("Configuration créée. Ne partagez ni lab_config.h ni le firmware contenant la clé.")


if __name__ == "__main__":
    configure()
