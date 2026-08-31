import argparse

from . import config, notify, rank, store, zotero
from .sources import arxiv, blogs, conferences, semantic_scholar


def digest() -> None:
    interests = config.load_interests()
    seen = store.load_seen()
    failures: list[str] = []

    candidates = arxiv.fetch(interests["arxiv_categories"])
    conf_papers, conf_failures = conferences.fetch(interests.get("venues", {}).get("top", []))
    posts, blog_failures = blogs.fetch(interests["blog_feeds"])
    recs, s2_failures = semantic_scholar.recommendations(interests["seed_papers"])
    failures.extend(conf_failures + blog_failures + s2_failures)

    fresh = store.unseen(conf_papers + candidates + posts + recs, seen)
    fresh = fresh[: interests["limits"]["max_candidates"]]
    if not fresh:
        return

    client = rank.get_client()
    picks = rank.rank(client, interests, fresh, interests["limits"]["max_picks_per_day"])

    if picks:
        failures.extend(zotero.push(picks))
    seen.update(c["id"] for c in fresh)
    store.save_seen(seen)
    notify.send_email("Daily papers", notify.format_digest(picks, failures))


def feedback() -> None:
    from . import feedback as fb
    added = fb.sync()
    print(f"seeds added: {added}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="envoy")
    parser.add_argument("command", choices=["digest", "feedback"])
    args = parser.parse_args()
    digest() if args.command == "digest" else feedback()


if __name__ == "__main__":
    main()
