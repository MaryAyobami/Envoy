import feedparser

MAX_PER_FEED = 10


def fetch(feeds: list[str]) -> tuple[list[dict], list[str]]:
    posts, failures = [], []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            failures.append(feed_url)
            continue
        site = parsed.feed.get("title", feed_url)
        for entry in parsed.entries[:MAX_PER_FEED]:
            link = entry.get("link", "")
            if not link:
                continue
            posts.append({
                "id": f"blog:{link}",
                "title": " ".join(entry.get("title", "untitled").split()),
                "abstract": " ".join(entry.get("summary", "").split())[:1500],
                "authors": [],
                "url": link,
                "source": site,
            })
    return posts, failures
