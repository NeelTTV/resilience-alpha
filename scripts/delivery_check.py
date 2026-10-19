"""Check handoff files; never infer physical or human validation."""

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    slug = project["delivery_slug"]
    output = ROOT / "output" / slug
    checks = {}
    hashes = {}
    for suffix in ["-Dossier.pdf", "-Pres.pptx", "-Code.zip"]:
        path = output / (slug + suffix)
        checks[suffix] = path.is_file() and path.stat().st_size > 1000
        if checks[suffix]:
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    archive = output / (slug + "-Code.zip")
    if checks["-Code.zip"]:
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read("resilience-alpha/MANIFEST.sha256.json"))
            checks["archive_integrity"] = bundle.testzip() is None and all(
                hashlib.sha256(bundle.read(name)).hexdigest() == digest
                for name, digest in manifest.items()
            )
            checks["archive_matches_sources"] = all(
                (ROOT / name.removeprefix("resilience-alpha/")).is_file()
                and hashlib.sha256(
                    (ROOT / name.removeprefix("resilience-alpha/")).read_bytes()
                ).hexdigest()
                == digest
                for name, digest in manifest.items()
                if not name.startswith("resilience-alpha/evidence/")
            )
            checks["no_secret_paths"] = not any(
                set(Path(name).parts).intersection({".secrets", ".env", ".venv"})
                for name in bundle.namelist()
            )
    for name in ["recovery", "security", "reproducibility", "browser"]:
        path = ROOT / "output/evidence" / (name + ".json")
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        checks[name] = bool(value) and value.get("passed", all(value.values())) is True
    acceptance = json.loads((ROOT / "docs/acceptance.json").read_text(encoding="utf-8"))
    pending = [
        item["label"]
        for item in acceptance.values()
        if item["validated"] is not True or not item["evidence"].strip()
    ]
    video = output / (slug + "-VidChrono.mp4")
    if not video.exists():
        pending.append("Fichier Clip Chrono MP4 absent")
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "automatic_checks": checks,
        "automatic_checks_passed": all(checks.values()),
        "human_validation_not_inferred": pending,
        "ready_for_submission": all(checks.values()) and not pending,
        "artifact_sha256": hashes,
    }
    destination = ROOT / "output/evidence/delivery-readiness.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "ETAT-DU-RENDU.txt").write_text(
        "Contrôles automatiques : "
        + ("OK" if all(checks.values()) else "ÉCHEC")
        + "\nValidations physiques et humaines non déduites des tests :\n"
        + "".join("- " + item + "\n" for item in pending)
        + "\nProcédure : docs/recette-terrain.md ; conducteur : docs/soutenance.md\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Fail until submission is complete")
    args = parser.parse_args()
    result = check()
    if not result["automatic_checks_passed"] or (
        args.strict and not result["ready_for_submission"]
    ):
        raise SystemExit(1)
