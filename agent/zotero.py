import os
from datetime import datetime

import requests

BASE = "https://api.zotero.org"
TIMEOUT = 30


def _auth() -> tuple[str, dict]:
    user_id = os.environ["ZOTERO_USER_ID"]
    headers = {"Zotero-API-Key": os.environ["ZOTERO_API_KEY"]}
    return user_id, headers


def _get_collections_map(user_id: str, headers: dict) -> list[dict]:
    try:
        response = requests.get(f"{BASE}/users/{user_id}/collections", headers=headers, timeout=TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


def _resolve_month_collection(user_id: str, headers: dict, parent_key: str, collections: list[dict]) -> tuple[str, list[dict]]:
    now = datetime.now()
    month_patterns = [
        now.strftime("%B %y'"),   # August 26'
        now.strftime("%B %Y"),    # August 2026
        now.strftime("%B %y"),    # August 26
        now.strftime("%Y-%m"),    # 2026-08
    ]

    for col in collections:
        d = col.get("data", {})
        if d.get("parentCollection") == parent_key:
            if any(d.get("name", "").lower() == pat.lower() for pat in month_patterns):
                month_key = d["key"]
                subtopics = [c for c in collections if c.get("data", {}).get("parentCollection") == month_key]
                return month_key, subtopics

    # Auto-create new month subcollection under parent if not found
    new_name = now.strftime("%B %y'")
    try:
        create_resp = requests.post(
            f"{BASE}/users/{user_id}/collections",
            json=[{"name": new_name, "parentCollection": parent_key}],
            headers=headers,
            timeout=TIMEOUT,
        )
        if create_resp.status_code in (200, 201):
            created = create_resp.json()
            success_keys = created.get("success", {})
            if success_keys:
                return list(success_keys.values())[0], []
    except Exception:
        pass

    return parent_key, []


def push(picks: list[dict]) -> list[str]:
    user_id, headers = _auth()
    parent_key = os.environ.get("ZOTERO_COLLECTION", "").strip()

    collections = _get_collections_map(user_id, headers) if parent_key else []
    month_key, subtopics = _resolve_month_collection(user_id, headers, parent_key, collections) if parent_key else ("", [])

    items = []
    for pick in picks:
        target_cols = [month_key] if month_key else []

        # Check if pick matches any topic subcollections under the current month
        text = f"{pick['title']} {pick.get('abstract', '')} {pick.get('note', '')}".lower()
        for sub in subtopics:
            topic_name = sub.get("data", {}).get("name", "").lower()
            topic_words = [w for w in topic_name.split() if len(w) > 3]
            if topic_words and all(w in text for w in topic_words):
                target_cols.append(sub["data"]["key"])

        items.append({
            "itemType": "journalArticle",
            "title": pick["title"],
            "creators": [
                {"creatorType": "author", "name": name} for name in pick["authors"][:20]
            ],
            "abstractNote": pick["abstract"][:5000],
            "url": pick["url"],
            "extra": f"source: {pick['source']} | agent score: {pick.get('score', '')}",
            "collections": list(set(target_cols)),
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
