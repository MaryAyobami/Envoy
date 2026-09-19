import os
import time

import requests

BASE = "https://api.semanticscholar.org"
FIELDS = "title,abstract,authors,url,venue,year,externalIds"
TIMEOUT = 15


def _headers() -> dict:
    key = os.environ.get("S2_API_KEY")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PaperAgent/1.0; +https://github.com)"}
    if key and key.strip():
        headers["x-api-key"] = key.strip()
    return headers


def resolve_seed(title: str) -> tuple[str | None, str | None]:
    headers = _headers()
    try:
        response = requests.get(
            f"{BASE}/graph/v1/paper/search",
            params={"query": title, "limit": 1, "fields": "paperId,title"},
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code == 429:
            return None, "rate_limited"
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"

        results = response.json().get("data", [])
        return (results[0]["paperId"] if results else None), None
    except Exception as e:
        return None, str(e)


def recommendations(seed_titles: list[str], per_seed: int = 10) -> tuple[list[dict], list[str]]:
    if not seed_titles:
        return [], []

    papers, failures = [], []
    has_api_key = bool(os.environ.get("S2_API_KEY", "").strip())
    rate_limited = False

    for title in seed_titles:
        if rate_limited:
            break

        paper_id, err = resolve_seed(title)
        if err == "rate_limited":
            rate_limited = True
            if not has_api_key:
                failures.append("Semantic Scholar rate-limited (set S2_API_KEY secret for graph recommendations)")
            else:
                failures.append("Semantic Scholar API rate-limited")
            break
        elif err:
            failures.append(f"Semantic Scholar ({title}): {err}")
            continue

        if not paper_id:
            continue

        time.sleep(0.5)
        try:
            response = requests.get(
                f"{BASE}/recommendations/v1/papers/forpaper/{paper_id}",
                params={"limit": per_seed, "fields": FIELDS},
                headers=_headers(),
                timeout=TIMEOUT,
            )
            if response.status_code == 429:
                rate_limited = True
                if not has_api_key:
                    failures.append("Semantic Scholar rate-limited (set S2_API_KEY secret for graph recommendations)")
                else:
                    failures.append("Semantic Scholar API rate-limited")
                break
            if response.status_code != 200:
                continue

            for paper in response.json().get("recommendedPapers", []):
                pid = paper.get("paperId")
                title_text = paper.get("title", "")
                if not pid or not title_text:
                    continue
                papers.append({
                    "id": f"s2:{pid}",
                    "title": title_text,
                    "abstract": paper.get("abstract") or "",
                    "authors": [a.get("name", "") for a in paper.get("authors", []) if isinstance(a, dict)],
                    "url": paper.get("url") or f"https://www.semanticscholar.org/paper/{pid}",
                    "source": paper.get("venue") or "Semantic Scholar",
                })
        except Exception as e:
            failures.append(f"Semantic Scholar ({title}): {e}")

    return papers, failures
