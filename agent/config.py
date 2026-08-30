from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEEN_PATH = DATA_DIR / "seen.json"
INTERESTS_PATH = ROOT / "interests.yaml"


def load_interests() -> dict:
    with open(INTERESTS_PATH) as f:
        return yaml.safe_load(f)
