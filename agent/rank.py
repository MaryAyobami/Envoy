import json
import os
import time

import groq

PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
_RESOLVED_MODEL: str | None = None
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

CRITICAL FILTERING & PRIORITY RULES:
- PRIORITY: Strongly favor and prioritize papers published in or accepted to top tracked systems and security conference proceedings (OSDI, SOSP, EuroSys, ASPLOS, NSDI, FAST, SIGMETRICS, USENIX Security, IEEE S&P, CCS, NDSS, USENIX ATC, SC, HPDC).
- Prioritize candidates that directly advance the primary research pillars: (1) Empirical performance variability/methodology/benchmarking, (2) Confidential computing/TEEs (TDX/SEV-SNP/SGX/Gramine/Attestation), (3) Cloud & HPC security/isolation.
- Reject pure or theoretical cryptography (proof systems, zero-knowledge math, cipher/signature schemes) unless it involves a concrete systems implementation, hardware TEE, or cloud/HPC workload evaluation.
- Reject blockchain, cryptocurrency, web3, and smart contract papers.
- Reject pure ML/NLP/CV model architectures that do not focus on systems performance, testbeds, or hardware acceleration.

Candidate papers and posts:
__CANDIDATES__

Pick at most __MAX_PICKS__ papers that score >= 7 (on a 1-10 scale) on relevance to this researcher's specific systems agenda, giving highest preference to top conference proceedings.
If no papers in this batch meet this relevance bar, return an empty array {"picks": []}.

Respond with ONLY a JSON object:
{"picks": [{"id": "<candidate id>", "score": <7-10>, "note": "<two sentences specifically explaining the direct connection to performance variability, TEEs, testbeds, or cloud/HPC security, noting the conference if applicable>"}]}"""


def get_client() -> groq.Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Get a free key at https://console.groq.com/keys")
    return groq.Groq(api_key=api_key)


def _build_prompt(interests: dict, chunk: list[dict], max_picks: int) -> str:
    listing = "\n".join(
        f"- [Venue/Source: {c.get('source', 'Preprint')}] ID: {c['id']} | Title: {c['title']} | Abstract: {c['abstract'][:500]}"
        for c in chunk
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


def _match_candidate(pick_item: dict, chunk: list[dict]) -> dict | None:
    raw_id = str(pick_item.get("id", "")).strip()
    clean_id = raw_id.split(":")[-1].strip() if ":" in raw_id else raw_id
    raw_title = str(pick_item.get("title", "")).strip().lower()

    for c in chunk:
        c_id = str(c.get("id", "")).strip()
        c_clean_id = c_id.split(":")[-1].strip() if ":" in c_id else c_id
        c_title = str(c.get("title", "")).strip().lower()

        if raw_id and (raw_id == c_id or raw_id == c_clean_id or clean_id == c_clean_id):
            return c
        if raw_title and (raw_title in c_title or c_title in raw_title):
            return c
        if raw_id and (raw_id.lower() in c_title or c_title in raw_id.lower()):
            return c
    return None


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

            matched_results = []
            for p in picks:
                if not isinstance(p, dict):
                    continue
                score = p.get("score", 7)
                try:
                    score = int(score)
                except (ValueError, TypeError):
                    score = 7

                if score < 7:
                    continue

                matched = _match_candidate(p, chunk)
                if matched:
                    matched_results.append({
                        **matched,
                        "score": score,
                        "note": str(p.get("note", "")).strip(),
                    })
            return matched_results
        except (groq.RateLimitError, groq.APIStatusError) as e:
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"Groq API error on chunk: {e}")
            return []
        except Exception as e:
            print(f"Unexpected ranking error on chunk: {e}")
            return []
    return []


def _resolve_model(client: groq.Groq) -> str:
    global _RESOLVED_MODEL
    if _RESOLVED_MODEL:
        return _RESOLVED_MODEL

    env_model = os.environ.get("GROQ_MODEL") or os.environ.get("LLM_MODEL")
    if env_model:
        _RESOLVED_MODEL = env_model.strip()
        return _RESOLVED_MODEL

    try:
        available = {m.id for m in client.models.list().data}
        for candidate in PREFERRED_MODELS:
            if candidate in available:
                _RESOLVED_MODEL = candidate
                print(f"[Envoy] Selected Groq model: {_RESOLVED_MODEL}")
                return _RESOLVED_MODEL
    except Exception:
        pass

    _RESOLVED_MODEL = PREFERRED_MODELS[0]
    return _RESOLVED_MODEL


def rank(client: groq.Groq, interests: dict, candidates: list[dict], max_picks: int) -> list[dict]:
    if not candidates:
        return []
    model = _resolve_model(client)

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
