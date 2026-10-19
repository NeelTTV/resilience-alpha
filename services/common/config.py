import os
from pathlib import Path


def secret(name: str) -> str:
    path = os.getenv(f"{name}_FILE")
    value = Path(path).read_text(encoding="utf-8").strip() if path else os.getenv(name, "")
    if not value:
        raise RuntimeError(f"Missing secret: {name}_FILE")
    return value

