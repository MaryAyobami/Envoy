import json
import os

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

PROMPT = """You select daily reading for a systems PhD student. Their interest profile:

{interests}

Candidate papers and posts (id, title, abstract):

{candidates}

Pick the {max_picks} most valuable items for this specific researcher. Prefer items matching
high-weight clusters and top venues; apply the downrank list. Respond with ONLY a JSON array:
[{{"id": "<candidate id>", "score": <1-10>, "note": "<two sentences on why this matters to THEIR work, not a generic summary>"}}]"""


def rank(client: anthropic.Anthropic, interests: dict, candidates: list[dict], max_picks: int) -> list[dict]:
    listing = "\n".join(
        f"- {c['id']} | {c['title']} | {c['abstract'][:600]}" for c in candidates
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                interests=json.dumps({k: interests[k] for k in ("clusters", "downrank", "venues")}),
                candidates=listing,
                max_picks=max_picks,
            ),
        }],
    )
    raw = message.content[0].text.strip()
    if "[" in raw and "]" in raw:
        raw = raw[raw.find("["):raw.rfind("]") + 1]
    picks = json.loads(raw)
    by_id = {c["id"]: c for c in candidates}
    return [
        {**by_id[p["id"]], "score": p["score"], "note": p["note"]}
        for p in picks if p["id"] in by_id
    ]
