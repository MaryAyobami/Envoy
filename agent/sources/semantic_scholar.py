import os
import time

import requests

BASE = "https://api.semanticscholar.org"
FIELDS = "title,abstract,authors,url,venue,year,externalIds"
TIMEOUT = 30


def _headers() -> dict:
    key = os.environ.get("S2_API_KEY")
    headers = {"User-Agent": "PaperAgent/1.0"}
    if key:
        headers["x-api-key"] = key
    return headers


def resolve_seed(title: str) -> str | None:
    for attempt in range(2):
        response = requests.get(
            f"{BASE}/graph/v1/paper/search",
            params={"query": title, "limit": 1, "fields": "paperId,title"},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if response.status_code == 429 and attempt == 0:
            time.sleep(2)
            continue
        response.raise_for_status()
        results = response.json().get("data", [])
        return results[0]["paperId"] if results else None
    return None


def recommendations(seed_titles: list[str], per_seed: int = 10) -> tuple[list[dict], list[str]]:
    papers, failures = [], []
    for title in seed_titles:
        try:
            paper_id = resolve_seed(title)
            if not paper_id:
                failures.append(f"seed not found: {title}")
                continue
            time.sleep(1)
            response = requests.get(
                f"{BASE}/recommendations/v1/papers/forpaper/{paper_id}",
                params={"limit": per_seed, "fields": FIELDS},
                headers=_headers(),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            for paper in response.json().get("recommendedPapers", []):
                papers.append({
                    "id": f"s2:{paper['paperId']}",
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract") or "",
                    "authors": [a["name"] for a in paper.get("authors", [])],
                    "url": paper.get("url", ""),
                    "source": paper.get("venue") or "Semantic Scholar",
                })
        except requests.RequestException as error:
            failures.append(f"{title}: {error}")
    return papers, failures
