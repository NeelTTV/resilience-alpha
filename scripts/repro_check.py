"""Deploy a fresh source snapshot with Ansible, without changing the running lab.

The temporary controller alone mounts Docker's socket for deployment. Applications
never receive it. All destructive cleanup is scoped to this run's random project.
"""

import hashlib
import json
import re
import socket
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

from package import DIRECTORIES, EXCLUDED, ROOT_FILES

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.check_output(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stderr=subprocess.STDOUT,
        **kwargs,
    )


def free_ports(count):
    sockets = [socket.socket() for _ in range(count)]
    try:
        for item in sockets:
            item.bind(("127.0.0.1", 0))
        return [item.getsockname()[1] for item in sockets]
    finally:
        for item in sockets:
            item.close()


def main():
    identifier = "ra-repro-" + uuid.uuid4().hex[:12]
    controller = identifier + "-controller"
    volume = identifier + "-source"
    temporary = ROOT / "tmp" / identifier
    temporary.mkdir(parents=True)
    snapshot = temporary / "source.zip"
    manifest = {}
    with zipfile.ZipFile(snapshot, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink() or EXCLUDED.intersection(relative.parts):
                continue
            if relative.parts[0] not in DIRECTORIES and relative.as_posix() not in ROOT_FILES:
                continue
            content = path.read_bytes()
            archive.writestr(relative.as_posix(), content)
            manifest[relative.as_posix()] = hashlib.sha256(content).hexdigest()
    evidence = {
        "scope": "Fresh source/secrets/volumes on the same Docker Desktop engine; not a second PC",
        "project": identifier,
        "source_files": manifest,
        "passed": False,
        "checks": {},
    }
    started = time.monotonic()
    created = False
    source = None
    try:
        print("Building temporary Ansible controller...", flush=True)
        (temporary / "controller-build.log").write_text(
            run(
                "docker",
                "build",
                "-f",
                "infra/ansible/controller.Dockerfile",
                "-t",
                "resilience-alpha-repro-controller",
                ".",
            ),
            encoding="utf-8",
        )
        run("docker", "volume", "create", volume)
        source = run("docker", "volume", "inspect", "-f", "{{.Mountpoint}}", volume).strip()
        if not re.fullmatch(r"/var/lib/docker/volumes/ra-repro-[a-f0-9]{12}-source/_data", source):
            raise RuntimeError("Unexpected Docker volume path; refusing deployment")
        run(
            "docker",
            "run",
            "-d",
            "--name",
            controller,
            "--mount",
            "type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock",
            "--mount",
            f"type=volume,source={volume},target={source}",
            "resilience-alpha-repro-controller",
        )
        created = True

        def execute(*args):
            return run("docker", "exec", "-w", source, controller, *args)

        run("docker", "cp", str(snapshot), controller + ":/tmp/source.zip")
        execute(
            "python", "-c", "import zipfile; zipfile.ZipFile('/tmp/source.zip').extractall('.')"
        )
        execute("python", "scripts/init-secrets.py")
        http, https, prometheus, grafana, ollama = free_ports(5)
        config = {
            "COMPOSE_PROJECT_NAME": identifier,
            "HTTP_PORT": http,
            "HTTPS_PORT": https,
            "PROMETHEUS_PORT": prometheus,
            "GRAFANA_PORT": grafana,
            "OLLAMA_PORT": ollama,
        }
        execute(
            "python",
            "-c",
            "from pathlib import Path; import json; "
            "p=Path('.env'); d=dict(line.split('=',1) for line in p.read_text().splitlines() "
            "if '=' in line and not line.startswith('#')); "
            "d.update(json.loads(__import__('sys').argv[1])); "
            "p.write_text(''.join(str(k)+'='+str(v)+'\\n' for k,v in d.items()))",
            json.dumps(config),
        )
        evidence["checks"]["fresh_secrets"] = True
        print("Deploying fresh project through Ansible...", flush=True)
        execute("ansible-galaxy", "collection", "install", "-r", "infra/ansible/requirements.yml")
        command = [
            "ansible-playbook",
            "-i",
            "infra/ansible/inventory.ini",
            "infra/ansible/deploy.yml",
        ]
        for label, extra in [("deploy", []), ("idempotence", ["-e", "deploy_build=never"])]:
            result = execute(*command, *extra)
            (temporary / (label + ".log")).write_text(result, encoding="utf-8")
            if not re.search(r"unreachable=0\s+failed=0", result):
                raise RuntimeError(f"Ansible {label} did not report success")
            if label == "idempotence" and not re.search(r"changed=0\s+unreachable=0", result):
                raise RuntimeError("Second Ansible deployment changed resources")
            evidence["checks"][label] = True
        run("docker", "network", "connect", identifier + "_backend", controller)
        result = run(
            "docker",
            "exec",
            "-e",
            "SMOKE_BASE_URL=http://waf:8080",
            "-w",
            source,
            controller,
            "python",
            "scripts/smoke.py",
        )
        (temporary / "smoke.log").write_text(result, encoding="utf-8")
        evidence["checks"]["business_smoke"] = "PASS:" in result
        # A separate host-side request confirms that the new published port works too.
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{http}/api/health", timeout=10) as response:
            evidence["checks"]["host_gateway"] = json.load(response)["database"] == "ok"
        evidence["passed"] = all(evidence["checks"].values())
        print("PASS: fresh Ansible deployment, unchanged second run and business flow.", flush=True)
    except subprocess.CalledProcessError as error:
        (temporary / "failure.log").write_text(error.output, encoding="utf-8")
        evidence["error"] = "Command failed; inspect the private tmp run directory"
        raise
    finally:
        if created:
            try:
                # project name and source are generated locally, never supplied by a user.
                run(
                    "docker",
                    "exec",
                    "-w",
                    source,
                    controller,
                    "docker",
                    "compose",
                    "-p",
                    identifier,
                    "down",
                    "--volumes",
                    "--remove-orphans",
                )
                evidence["cleanup"] = "isolated project removed"
            finally:
                run("docker", "rm", "-f", controller)
                run("docker", "volume", "rm", volume)
        evidence["duration_seconds"] = round(time.monotonic() - started, 2)
        destination = ROOT / "output/evidence/reproducibility.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
