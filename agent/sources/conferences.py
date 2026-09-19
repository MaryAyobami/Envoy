import time
import urllib.parse
import feedparser
import requests

DBLP_BASE = "https://dblp.org/search/publ/api"
ARXIV_API = "https://export.arxiv.org/api/query"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaperAgent/1.0; +https://github.com)"}
TIMEOUT = 3

# Map friendly conference names to DBLP stream keys
VENUE_MAP = {
    "OSDI": "osdi",
    "SOSP": "sosp",
    "EuroSys": "eurosys",
    "ASPLOS": "asplos",
    "NSDI": "nsdi",
    "FAST": "fast",
    "SIGMETRICS": "sigmetrics",
    "USENIX ATC": "atc",
    "IEEE S&P": "sp",
    "USENIX Security": "sec",
    "CCS": "ccs",
    "NDSS": "ndss",
    "PETS": "pets",
    "SoCC": "socc",
    "SC": "sc",
    "HPDC": "hpdc",
    "SysTEX": "systex",
    "HotOS": "hotos",
}


def fetch_dblp_papers(venue_name: str, stream_key: str, years: str = "2025|2026", max_per_venue: int = 8) -> tuple[list[dict], bool]:
    query = f"stream:conf/{stream_key}: year:{years}"
    params = {
        "q": query,
        "format": "json",
        "h": max_per_venue,
    }
    try:
        response = requests.get(DBLP_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code != 200:
            return [], False

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            # DBLP blocked by bot challenge or returning HTML
            return [], False

        hits = response.json().get("result", {}).get("hits", {}).get("hit", [])
        papers = []
        for hit in hits:
            info = hit.get("info", {})
            title = info.get("title", "").rstrip(".")
            if not title:
                continue

            raw_authors = info.get("authors", {}).get("author", [])
            if isinstance(raw_authors, dict):
                raw_authors = [raw_authors]
            authors = [a.get("text", "") for a in raw_authors if isinstance(a, dict)]

            year = str(info.get("year", "2026"))
            venue_display = f"{venue_name} '{year[-2:]}" if len(year) == 4 else f"{venue_name} {year}"
            paper_id = hit.get("@id") or f"dblp:{info.get('key', title)}"
            url = info.get("ee") or info.get("url") or f"https://dblp.org/rec/{info.get('key', '')}"

            papers.append({
                "id": f"conf:{paper_id}",
                "title": title,
                "abstract": f"Published in peer-reviewed conference proceedings at {venue_display}. Research on systems, security, and computing infrastructure.",
                "authors": authors,
                "url": url,
                "source": venue_display,
            })
        return papers, True
    except Exception:
        return [], False


def fetch_arxiv_conf_papers(tracked_venues: list[str], max_results: int = 50) -> list[dict]:
    if not tracked_venues:
        return []
    conf_terms = [f'"{v}"' if " " in v else v for v in tracked_venues]
    conf_query = " OR ".join(f"all:{c}" for c in conf_terms)
    cat_query = "cat:cs.OS OR cat:cs.DC OR cat:cs.PF OR cat:cs.CR OR cat:cs.AR"
    query = f"({cat_query}) AND ({conf_query})"
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    try:
        feed = feedparser.parse(url)
        papers = []
        for entry in feed.entries:
            arxiv_id = entry.id.split("/abs/")[-1]
            comment = entry.get("arxiv_comment", "")
            journal_ref = entry.get("arxiv_journal_ref", "")

            matched_venue = None
            for v in tracked_venues:
                if v.lower() in comment.lower() or v.lower() in journal_ref.lower():
                    matched_venue = v
                    break

            source_label = f"arXiv ({matched_venue})" if matched_venue else "arXiv (Conf Track)"
            papers.append({
                "id": f"arxiv:{arxiv_id}",
                "title": " ".join(entry.title.split()),
                "abstract": " ".join(entry.summary.split()),
                "authors": [a.name for a in entry.get("authors", [])],
                "url": entry.link,
                "source": source_label,
            })
        return papers
    except Exception:
        return []


def fetch(tracked_venues: list[str], max_per_venue: int = 5) -> tuple[list[dict], list[str]]:
    papers: list[dict] = []
    seen_ids: set[str] = set()

    # 1. Fetch conference-tagged papers from arXiv
    arxiv_conf = fetch_arxiv_conf_papers(tracked_venues, max_results=40)
    for p in arxiv_conf:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            papers.append(p)

    # 2. Try DBLP for top venues (with fast-fail if blocked)
    for venue in tracked_venues:
        stream_key = VENUE_MAP.get(venue) or venue.lower()
        venue_papers, ok = fetch_dblp_papers(venue, stream_key, max_per_venue=max_per_venue)
        if venue_papers:
            for p in venue_papers:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    papers.append(p)
        if not ok:
            # DBLP is blocked or unavailable; avoid waiting on multiple timeouts
            break
        time.sleep(0.1)

    return papers, []
