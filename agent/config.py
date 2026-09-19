import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEEN_PATH = DATA_DIR / "seen.json"
INTERESTS_PATH = ROOT / "interests.yaml"
ENV_PATH = ROOT / ".env"


def _load_env() -> None:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


_load_env()


def load_interests() -> dict:
    with open(INTERESTS_PATH) as f:
        return yaml.safe_load(f)

