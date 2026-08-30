import json
import os
import time

import groq

DEFAULT_MODEL = "openai/gpt-oss-120b"
CHUNK_SIZE = 25

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


def _rank_chunk(client: groq.Groq, model: str, interests_json: str, chunk: list[dict], max_picks: int) -> list[dict]:
    listing = "\n".join(
        f"- {c['id']} | {c['title']} | {c['abstract'][:500]}" for c in chunk
    )
    for attempt in range(4):
        try:
            chat_completion = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": PROMPT.format(
                        interests=interests_json,
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

            by_id = {c["id"]: c for c in chunk}
            return [
                {**by_id[p["id"]], "score": p.get("score", 8), "note": p.get("note", "")}
                for p in picks
                if isinstance(p, dict) and p.get("id") in by_id
            ]
        except (groq.RateLimitError, groq.APIStatusError):
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    return []


def rank(client: groq.Groq, interests: dict, candidates: list[dict], max_picks: int) -> list[dict]:
    if not candidates:
        return []
    model = os.environ.get("GROQ_MODEL") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    interests_json = json.dumps({k: interests[k] for k in ("clusters", "downrank", "venues")})

    if len(candidates) <= CHUNK_SIZE:
        return _rank_chunk(client, model, interests_json, candidates, max_picks)

    all_picks = []
    for i in range(0, len(candidates), CHUNK_SIZE):
        chunk = candidates[i:i + CHUNK_SIZE]
        chunk_picks = _rank_chunk(client, model, interests_json, chunk, max_picks=max_picks)
        all_picks.extend(chunk_picks)
        time.sleep(0.5)

    all_picks.sort(key=lambda p: p.get("score", 0), reverse=True)
    seen_ids = set()
    deduped = []
    for p in all_picks:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            deduped.append(p)
    return deduped[:max_picks]
