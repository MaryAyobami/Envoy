import urllib.parse
import feedparser

API = "https://export.arxiv.org/api/query"
PAGE_SIZE = 100


def fetch(categories: list[str], max_results: int = 200) -> list[dict]:
    query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": min(max_results, PAGE_SIZE),
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    feed = feedparser.parse(url)
    papers = []
    for entry in feed.entries:
        arxiv_id = entry.id.split("/abs/")[-1]
        comment = entry.get("arxiv_comment", "")
        journal_ref = entry.get("arxiv_journal_ref", "")
        source = "arXiv"
        for v in ["OSDI", "SOSP", "EuroSys", "ASPLOS", "NSDI", "FAST", "SIGMETRICS", "USENIX Security", "IEEE S&P", "CCS", "NDSS", "PETS", "SoCC", "SC", "HPDC"]:
            if v.lower() in comment.lower() or v.lower() in journal_ref.lower():
                source = f"arXiv ({v})"
                break

        papers.append({
            "id": f"arxiv:{arxiv_id}",
            "title": " ".join(entry.title.split()),
            "abstract": " ".join(entry.summary.split()),
            "authors": [a.name for a in entry.get("authors", [])],
            "url": entry.link,
            "source": source,
        })
    return papers
