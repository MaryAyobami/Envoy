import os
from datetime import datetime

import requests

BASE = "https://api.zotero.org"
TIMEOUT = 30


def is_configured() -> bool:
    return bool(os.environ.get("ZOTERO_USER_ID", "").strip() and os.environ.get("ZOTERO_API_KEY", "").strip())


def _auth() -> tuple[str, dict]:
    user_id = os.environ.get("ZOTERO_USER_ID", "").strip()
    api_key = os.environ.get("ZOTERO_API_KEY", "").strip()
    if not user_id or not api_key:
        raise ValueError("Zotero credentials (ZOTERO_USER_ID, ZOTERO_API_KEY) are not configured.")
    headers = {"Zotero-API-Key": api_key}
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
        payload = [{"name": new_name}]
        if parent_key:
            payload[0]["parentCollection"] = parent_key

        create_resp = requests.post(
            f"{BASE}/users/{user_id}/collections",
            json=payload,
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
    if not is_configured():
        return []

    try:
        user_id, headers = _auth()
    except Exception as e:
        return [str(e)]

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

        creators = []
        for name in pick.get("authors", [])[:20]:
            if name:
                creators.append({"creatorType": "author", "name": name})

        items.append({
            "itemType": "journalArticle",
            "title": pick["title"],
            "creators": creators,
            "abstractNote": pick.get("abstract", "")[:5000],
            "url": pick.get("url", ""),
            "extra": f"source: {pick.get('source', '')} | agent score: {pick.get('score', '')}",
            "collections": [c for c in set(target_cols) if c],
            "tags": [{"tag": "agent-inbox"}],
        })

    if not items:
        return []

    try:
        response = requests.post(
            f"{BASE}/users/{user_id}/items", json=items, headers=headers, timeout=TIMEOUT
        )
        if response.status_code not in (200, 201):
            return [f"Zotero push returned HTTP {response.status_code}: {response.text[:200]}"]
        failed = response.json().get("failed", {})
        return [f"{items[int(i)]['title']}: {err.get('message', 'Failed to add')}" for i, err in failed.items() if int(i) < len(items)]
    except requests.RequestException as e:
        return [f"Zotero push failed: {e}"]


def liked_titles(tag: str = "keep", limit: int = 50) -> list[str]:
    if not is_configured():
        return []
    try:
        user_id, headers = _auth()
        response = requests.get(
            f"{BASE}/users/{user_id}/items",
            params={"tag": tag, "limit": limit, "sort": "dateAdded", "direction": "desc"},
            headers=headers, timeout=TIMEOUT,
        )
        if response.status_code != 200:
            return []
        return [item["data"]["title"] for item in response.json() if item.get("data", {}).get("title")]
    except Exception:
        return []
