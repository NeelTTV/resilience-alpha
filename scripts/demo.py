"""Local integration proof using an isolated attacker container (not a second physical PC)."""

import ipaddress
import json
import random
import subprocess
import time
import uuid
from urllib.error import HTTPError

from smoke import ROOT, request

if __name__ == "__main__":
    token = request(
        "/auth/token",
        {"username": "operator", "password": (ROOT / ".secrets/demo_password").read_text().strip()},
    )["access_token"]
    headers = {"Authorization": "Bearer " + token}
    initial = request("/control/status", headers=headers)
    if not initial["model"]:
        raise SystemExit("Train first: python scripts/calibrate.py")
    known = {i["id"] for i in initial["incidents"]}
    before = request(
        "/api/transactions",
        {"amount_cents": 123, "currency": "EUR"},
        {
            **headers,
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    config = json.loads(
        subprocess.check_output(
            [
                "docker",
                "compose",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
        )
    )
    network = config["networks"]["backend"]["name"]
    network_info = json.loads(
        subprocess.check_output(
            [
                "docker",
                "network",
                "inspect",
                network,
            ]
        )
    )[0]
    subnet = ipaddress.ip_network(network_info["IPAM"]["Config"][0]["Subnet"])
    used = {
        entry["IPv4Address"].split("/")[0] for entry in network_info.get("Containers", {}).values()
    }
    used.update(i["source_ip"] for i in initial["incidents"])
    used.update(initial["model"].get("protected_sources", []))
    candidates = [
        str(subnet.network_address + index)
        for index in range(32, min(230, subnet.num_addresses - 1))
    ]
    random.SystemRandom().shuffle(candidates)
    attack_ip = next(ip for ip in candidates if ip not in used)
    attack = subprocess.Popen(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            "--ip",
            attack_ip,
            "--mount",
            "type=bind,source="
            + str(ROOT / "security/scenarios/request_flood.py")
            + ",target=/attack.py,readonly",
            "python:3.12-slim",
            "python",
            "/attack.py",
            "--target",
            "http://waf:8080",
            "--lab-host",
            "waf",
            "--seconds",
            "35",
            "--rps",
            "70",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    start = time.time()
    failures = 0
    recovered_during_attack = False
    incident = None
    observations = []
    try:
        while time.time() - start < 70:
            business_ok = False
            try:
                request("/api/transactions", headers=headers)
                business_ok = True
            except HTTPError as exc:
                if exc.code == 503:
                    failures += 1
                else:
                    raise
            status = request("/control/status", headers=headers)
            new = [
                i
                for i in status["incidents"]
                if i["id"] not in known and i["source_ip"] == attack_ip
            ]
            incident = new[0] if new else None
            observations.append(
                {
                    "at": time.time(),
                    "business_ok": business_ok,
                    "incident_state": incident["state"] if incident else None,
                }
            )
            if incident and incident["state"] == "recovered":
                recovered_during_attack = attack.poll() is None
                break
            if incident and incident["state"] == "failed":
                break
            time.sleep(0.5)
    finally:
        stdout, stderr = attack.communicate(timeout=45)
    evidence = {
        "scope": "local Docker integration; second physical PC remains to validate",
        "attacker_ip": attack_ip,
        "before_transaction": before,
        "incident": incident,
        "observed_503": failures,
        "recovered_while_attack_running": recovered_during_attack,
        "observations": observations,
        "attack": json.loads(stdout) if stdout.strip() else stderr,
    }
    history = request("/api/transactions", headers=headers)
    evidence["previous_transaction_preserved"] = any(t["id"] == before["id"] for t in history)
    evidence["passed"] = bool(
        incident
        and incident["state"] == "recovered"
        and failures > 0
        and recovered_during_attack
        and evidence["previous_transaction_preserved"]
    )
    path = ROOT / "output/evidence/recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2))
    print(json.dumps({k: v for k, v in evidence.items() if k != "observations"}, indent=2))
    if not evidence["passed"]:
        raise SystemExit("Recovery proof incomplete; inspect output/evidence/recovery.json")
