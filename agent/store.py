import json

from .config import SEEN_PATH


def load_seen() -> set[str]:
    if SEEN_PATH.exists():
        return set(json.loads(SEEN_PATH.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=0) + "\n")


def unseen(candidates: list[dict], seen: set[str]) -> list[dict]:
    return [c for c in candidates if c["id"] not in seen]
