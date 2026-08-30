import json
import os

import groq

DEFAULT_MODEL = "llama-3.3-70b-versatile"

PROMPT = """You select daily reading for a systems PhD student. Their interest profile:

{interests}

Candidate papers and posts (id, title, abstract):

{candidates}

Pick the {max_picks} most valuable items for this specific researcher. Prefer items matching
high-weight clusters and top venues; apply the downrank list. Respond with ONLY a JSON object with a "picks" array:
{{"picks": [{{"id": "<candidate id>", "score": <1-10>, "note": "<two sentences on why this matters to THEIR work, not a generic summary>"}}]}}"""


def get_client() -> groq.Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Get a free key at https://console.groq.com/keys")
    return groq.Groq(api_key=api_key)


def rank(client: groq.Groq, interests: dict, candidates: list[dict], max_picks: int) -> list[dict]:
    model = os.environ.get("GROQ_MODEL") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    listing = "\n".join(
        f"- {c['id']} | {c['title']} | {c['abstract'][:600]}" for c in candidates
    )
    chat_completion = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                interests=json.dumps({k: interests[k] for k in ("clusters", "downrank", "venues")}),
                candidates=listing,
                max_picks=max_picks,
            ),
        }],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = chat_completion.choices[0].message.content.strip()
    data = json.loads(raw)
    picks = data.get("picks", data) if isinstance(data, dict) else data
    if isinstance(picks, dict):
        for v in picks.values():
            if isinstance(v, list):
                picks = v
                break
    if not isinstance(picks, list):
        picks = []

    by_id = {c["id"]: c for c in candidates}
    return [
        {**by_id[p["id"]], "score": p.get("score", 8), "note": p.get("note", "")}
        for p in picks
        if isinstance(p, dict) and p.get("id") in by_id
    ]
