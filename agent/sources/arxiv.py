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
        papers.append({
            "id": f"arxiv:{arxiv_id}",
            "title": " ".join(entry.title.split()),
            "abstract": " ".join(entry.summary.split()),
            "authors": [a.name for a in entry.get("authors", [])],
            "url": entry.link,
            "source": "arXiv",
        })
    return papers
