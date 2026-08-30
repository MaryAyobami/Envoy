import yaml

from . import zotero
from .config import INTERESTS_PATH

MAX_SEEDS = 15


def sync() -> int:
    liked = zotero.liked_titles()
    if not liked:
        return 0
    with open(INTERESTS_PATH) as f:
        interests = yaml.safe_load(f)
    seeds = interests.get("seed_papers", [])
    added = [title for title in liked if title not in seeds]
    if not added:
        return 0
    interests["seed_papers"] = (seeds + added)[-MAX_SEEDS:]
    with open(INTERESTS_PATH, "w") as f:
        yaml.safe_dump(interests, f, sort_keys=False, allow_unicode=True, width=100)
    return len(added)
