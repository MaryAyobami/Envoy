import argparse
import os

from . import config, notify, rank, store, zotero
from .sources import arxiv, blogs, conferences, semantic_scholar


def digest() -> None:
    print("[Envoy] Starting daily literature digest...")
    interests = config.load_interests()
    seen = store.load_seen()
    failures: list[str] = []

    # 1. Ingest candidates from all sources
    print("[Envoy] Fetching candidates from arXiv...")
    candidates = arxiv.fetch(interests.get("arxiv_categories", []))
    print(f"[Envoy] Fetched {len(candidates)} arXiv preprints")

    print("[Envoy] Fetching venue proceedings and conference-tagged papers...")
    conf_papers, conf_failures = conferences.fetch(interests.get("venues", {}).get("top", []))
    print(f"[Envoy] Fetched {len(conf_papers)} conference papers")
    failures.extend(conf_failures)

    print("[Envoy] Fetching tech blog posts...")
    posts, blog_failures = blogs.fetch(interests.get("blog_feeds", []))
    print(f"[Envoy] Fetched {len(posts)} blog posts")
    failures.extend(blog_failures)

    print("[Envoy] Querying Semantic Scholar recommendations...")
    recs, s2_failures = semantic_scholar.recommendations(interests.get("seed_papers", []))
    print(f"[Envoy] Fetched {len(recs)} Semantic Scholar recommendations")
    failures.extend(s2_failures)

    all_raw = conf_papers + candidates + posts + recs
    # Deduplicate raw candidates by ID
    deduped_raw = []
    seen_raw_ids = set()
    for item in all_raw:
        item_id = item.get("id")
        if item_id and item_id not in seen_raw_ids:
            seen_raw_ids.add(item_id)
            deduped_raw.append(item)

    fresh = store.unseen(deduped_raw, seen)
    max_candidates = interests.get("limits", {}).get("max_candidates", 300)
    fresh = fresh[:max_candidates]
    print(f"[Envoy] {len(fresh)} fresh unseen candidates to evaluate (out of {len(deduped_raw)} collected)")

    picks: list[dict] = []
    if fresh:
        if not os.environ.get("GROQ_API_KEY"):
            msg = "GROQ_API_KEY is not set. Unable to rank candidate papers."
            print(f"[Envoy] {msg}")
            failures.append(msg)
        else:
            try:
                client = rank.get_client()
                max_picks = interests.get("limits", {}).get("max_picks_per_day", 4)
                print(f"[Envoy] Ranking candidates with Groq LLM (max picks: {max_picks})...")
                picks = rank.rank(client, interests, fresh, max_picks)
                print(f"[Envoy] Selected {len(picks)} top recommendations")
                seen.update(c["id"] for c in fresh)
                store.save_seen(seen)
            except Exception as e:
                msg = f"Groq ranking error: {e}"
                print(f"[Envoy] {msg}")
                failures.append(msg)
    else:
        print("[Envoy] No new unseen candidates found today.")

    # 2. Push to Zotero if configured
    if picks and zotero.is_configured():
        print(f"[Envoy] Pushing {len(picks)} picks to Zotero...")
        zotero_failures = zotero.push(picks)
        failures.extend(zotero_failures)

    # 3. Format and dispatch digest
    digest_text = notify.format_digest(picks, failures)
    subject = f"Envoy Daily Digest: {len(picks)} paper{'s' if len(picks) != 1 else ''}"
    notify.send_email(subject, digest_text)
    print("[Envoy] Daily digest run completed.")


def feedback() -> None:
    from . import feedback as fb
    added = fb.sync()
    print(f"[Envoy] Seed papers added: {added}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="envoy")
    parser.add_argument("command", choices=["digest", "feedback"])
    args = parser.parse_args()
    digest() if args.command == "digest" else feedback()


if __name__ == "__main__":
    main()
