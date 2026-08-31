import json
import os
import time

import groq

DEFAULT_MODEL = "openai/gpt-oss-120b"
CHUNK_SIZE = 25

PROMPT_TEMPLATE = """You are a rigorous literature recommender for a computer systems PhD researcher.

RESEARCH PROFILE:
__PROFILE__

WEIGHTED RESEARCH CLUSTERS:
__CLUSTERS__

ANCHOR SEED PAPERS:
__SEEDS__

TRACKED CONFERENCES & VENUES:
__VENUES__

EXPLICIT DOWNRANK / EXCLUSION LIST:
__DOWNRANK__

CRITICAL FILTERING RULES:
- Reject pure or theoretical cryptography (proof systems, zero-knowledge math, cipher/signature schemes) unless it involves a concrete systems implementation, hardware TEE (TDX/SEV-SNP/SGX), or cloud/HPC workload evaluation.
- Reject blockchain, cryptocurrency, web3, and smart contract papers.
- Reject pure ML/NLP/CV model architectures that do not focus on systems performance, testbeds, or hardware acceleration.
- Only select candidates that directly advance the primary pillars: Empirical performance variability/methodology, Confidential computing/TEEs, or Cloud/HPC workload security.

Candidate papers and posts:
__CANDIDATES__

Pick at most __MAX_PICKS__ papers that score >= 8 on relevance to this researcher's specific systems agenda.
If no papers in this batch meet this high bar, return an empty array {"picks": []}.

Respond with ONLY a JSON object:
{"picks": [{"id": "<candidate id>", "score": <1-10>, "note": "<two sentences specifically explaining the direct connection to performance variability, TEEs, testbeds, or cloud/HPC security>"}]}"""


def get_client() -> groq.Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Get a free key at https://console.groq.com/keys")
    return groq.Groq(api_key=api_key)


def _build_prompt(interests: dict, chunk: list[dict], max_picks: int) -> str:
    listing = "\n".join(
        f"- {c['id']} | {c['title']} | {c['abstract'][:500]}" for c in chunk
    )
    return (
        PROMPT_TEMPLATE
        .replace("__PROFILE__", json.dumps(interests.get("profile", {})))
        .replace("__CLUSTERS__", json.dumps(interests.get("clusters", [])))
        .replace("__SEEDS__", json.dumps(interests.get("seed_papers", [])))
        .replace("__VENUES__", json.dumps(interests.get("venues", {})))
        .replace("__DOWNRANK__", json.dumps(interests.get("downrank", [])))
        .replace("__CANDIDATES__", listing)
        .replace("__MAX_PICKS__", str(max_picks))
    )


def _rank_chunk(client: groq.Groq, model: str, prompt_text: str, chunk: list[dict]) -> list[dict]:
    for attempt in range(4):
        try:
            chat_completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"},
                temperature=0.1,
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
                if isinstance(p, dict) and p.get("id") in by_id and p.get("score", 0) >= 7
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

    if len(candidates) <= CHUNK_SIZE:
        prompt_text = _build_prompt(interests, candidates, max_picks)
        return _rank_chunk(client, model, prompt_text, candidates)

    all_picks = []
    for i in range(0, len(candidates), CHUNK_SIZE):
        chunk = candidates[i:i + CHUNK_SIZE]
        prompt_text = _build_prompt(interests, chunk, max_picks)
        chunk_picks = _rank_chunk(client, model, prompt_text, chunk)
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
