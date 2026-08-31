import time
import requests

DBLP_BASE = "https://dblp.org/search/publ/api"
HEADERS = {"User-Agent": "PaperAgent/1.0"}
TIMEOUT = 8

# Map friendly conference names to DBLP stream keys
VENUE_MAP = {
    "OSDI": "osdi",
    "SOSP": "sosp",
    "EuroSys": "eurosys",
    "ASPLOS": "asplos",
    "NSDI": "nsdi",
    "FAST": "fast",
    "SIGMETRICS": "sigmetrics",
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


def fetch_venue_papers(venue_name: str, stream_key: str, years: str = "2025|2026", max_per_venue: int = 8) -> list[dict]:
    query = f"stream:conf/{stream_key}: year:{years}"
    params = {
        "q": query,
        "format": "json",
        "h": max_per_venue,
    }
    response = requests.get(DBLP_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        return []

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

        year = info.get("year", "2026")
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
    return papers


def fetch(tracked_venues: list[str], max_per_venue: int = 5) -> tuple[list[dict], list[str]]:
    papers, failures = [], []
    for venue in tracked_venues:
        stream_key = VENUE_MAP.get(venue) or venue.lower()
        try:
            venue_papers = fetch_venue_papers(venue, stream_key, max_per_venue=max_per_venue)
            papers.extend(venue_papers)
            time.sleep(0.5)
        except Exception as e:
            failures.append(f"{venue}: {e}")
    return papers, failures
