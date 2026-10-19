"""Limited executor: one allowlisted action, no Docker socket or arbitrary command API."""

import asyncio
import hmac
import ipaddress
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, IPvAnyAddress

from services.common.config import secret

app = FastAPI(title="Restricted Ansible executor")
lock = asyncio.Lock()


class Quarantine(BaseModel):
    incident_id: UUID
    source_ip: IPvAnyAddress


def permitted(source):
    address = ipaddress.ip_address(str(source))
    networks = os.getenv("LAB_CIDRS", "172.16.0.0/12,192.168.137.0/24").split(",")
    return not (address.is_loopback or address.is_multicast or address.is_unspecified) and any(
        address in ipaddress.ip_network(network.strip()) for network in networks
    )


@app.get("/health")
def health():
    return {"status": "ok", "action": "quarantine_source", "ttl_seconds": 300}


@app.post("/quarantine")
async def quarantine(body: Quarantine, x_remediation_key: str = Header(default="")):
    if not hmac.compare_digest(x_remediation_key, secret("REMEDIATION_KEY")):
        raise HTTPException(401, "Executor authentication required")
    if not permitted(body.source_ip):
        raise HTTPException(422, "Source outside approved lab CIDRs")
    async with lock:
        path = Path(os.getenv("POLICY_FILE", "/policy/blocks.json"))
        rules = json.loads(path.read_text()) if path.exists() else []
        now = time.time()
        rules = [r for r in rules if r["expires_at"] > now]
        if any(r["incident_id"] == str(body.incident_id) for r in rules):
            return {"action": "quarantine_source", "replayed": True}
        if len(rules) >= 50:
            raise HTTPException(503, "Quarantine capacity reached")
        rule = {
            "ip": str(body.source_ip),
            "incident_id": str(body.incident_id),
            "expires_at": now + 300,
        }
        rules = [r for r in rules if r["ip"] != rule["ip"]] + [rule]
        # Ansible 2.19 resolves /dev/stdin to a pipe path; use a private temporary JSON file.
        with tempfile.TemporaryDirectory(prefix="quarantine-") as directory:
            variables = Path(directory) / "vars.json"
            variables.write_text(json.dumps({"blocks": rules}), encoding="utf-8")
            variables.chmod(0o600)
            process = await asyncio.create_subprocess_exec(
                "ansible-playbook",
                "-i",
                "localhost,",
                "-c",
                "local",
                "/app/infra/ansible/quarantine.yml",
                "--extra-vars",
                "@" + str(variables),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 20)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise HTTPException(504, "Ansible timed out") from None
            if process.returncode:
                logging.getLogger("uvicorn.error").error(
                    "Ansible failed: %s %s",
                    output.decode()[-2000:],
                    errors.decode()[-2000:],
                )
                raise HTTPException(502, "Ansible quarantine failed; inspect executor logs")
        if not path.exists() or json.loads(path.read_text()) != rules:
            raise HTTPException(502, "Ansible did not publish the expected policy")
        return {
            "action": "quarantine_source",
            "source_ip": rule["ip"],
            "expires_at": rule["expires_at"],
            "executor": "ansible.builtin.copy",
        }
