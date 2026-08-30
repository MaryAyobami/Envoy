import os

import requests

BASE = "https://api.zotero.org"
TIMEOUT = 30


def _auth() -> tuple[str, dict]:
    user_id = os.environ["ZOTERO_USER_ID"]
    headers = {"Zotero-API-Key": os.environ["ZOTERO_API_KEY"]}
    return user_id, headers


def push(picks: list[dict]) -> list[str]:
    user_id, headers = _auth()
    collection = os.environ.get("ZOTERO_COLLECTION", "")
    items = []
    for pick in picks:
        items.append({
            "itemType": "journalArticle",
            "title": pick["title"],
            "creators": [
                {"creatorType": "author", "name": name} for name in pick["authors"][:20]
            ],
            "abstractNote": pick["abstract"][:5000],
            "url": pick["url"],
            "extra": f"source: {pick['source']} | agent score: {pick.get('score', '')}",
            "collections": [collection] if collection else [],
            "tags": [{"tag": "agent-inbox"}],
        })
    response = requests.post(
        f"{BASE}/users/{user_id}/items", json=items, headers=headers, timeout=TIMEOUT
    )
    response.raise_for_status()
    failed = response.json().get("failed", {})
    return [f"{items[int(i)]['title']}: {err['message']}" for i, err in failed.items()]


def liked_titles(tag: str = "keep", limit: int = 50) -> list[str]:
    user_id, headers = _auth()
    response = requests.get(
        f"{BASE}/users/{user_id}/items",
        params={"tag": tag, "limit": limit, "sort": "dateAdded", "direction": "desc"},
        headers=headers, timeout=TIMEOUT,
    )
    response.raise_for_status()
    return [item["data"]["title"] for item in response.json() if item["data"].get("title")]
