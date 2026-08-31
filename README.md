# Envoy

Daily reading recommendations for systems researchers. Pulls new papers from top 2025/2026 conference proceedings (OSDI, SOSP, EuroSys, USENIX Security, IEEE S&P, ASPLOS, FAST, NSDI, SC), arXiv preprints, Semantic Scholar recommendations, and tech-blog feeds; ranks them against an interest profile using fast open-weights LLMs via Groq (Llama 3.3 70B); emails a short digest; and files each pick into a Zotero collection ready to read.

## How it works

- `interests.yaml` is the brain: weighted keyword clusters, venues, seed papers, blog feeds, and daily limits. Edit this, not the code.
- `daily-digest` (12:00 UTC) fetches candidates from conference proceedings, arXiv, blogs, and Semantic Scholar; drops anything already seen; sends one batched ranking call to Groq; pushes top picks to Zotero (organized by month & topic); and emails the digest with a per-pick note on why it matters to you.
- `weekly-feedback` (Sundays) reads papers you tagged `keep` in Zotero, folds them into `seed_papers`, and opens a PR so you approve changes to your own profile. Recommendations tighten as seeds accumulate.
- Feed failures appear in the digest instead of being swallowed.

## Setup

1. Groq: create a free API key at [console.groq.com/keys](https://console.groq.com/keys).
2. Zotero: create an API key with write access at [zotero.org/settings/keys](https://www.zotero.org/settings/keys); note your userID from the same page. Optionally set `ZOTERO_COLLECTION` to your reading folder key (e.g. `BG2ZPBL6` for General Reading).
3. Add repository secrets: `GROQ_API_KEY`, `ZOTERO_API_KEY`, `ZOTERO_USER_ID`, `ZOTERO_COLLECTION` (optional), `GROQ_MODEL` (optional), `S2_API_KEY` (optional), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `NOTIFY_EMAIL`.
4. Adjust `interests.yaml` (clusters, feeds, `max_picks_per_day`) and trigger `daily-digest` manually once.

Rating workflow: tag a good paper `keep` in Zotero; delete duds. That is the entire feedback interface.

## Local run

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your_groq_key"
export ZOTERO_API_KEY="your_zotero_key"
export ZOTERO_USER_ID="your_zotero_user_id"
python -m agent.main digest
python -m agent.main feedback
```

## Layout

```
agent/
  config.py                    paths, interest loading
  sources/conferences.py       direct 2025/2026 proceedings for top venues
  sources/arxiv.py             new submissions by category & conf acceptance
  sources/blogs.py             RSS/Atom tech blogs
  sources/semantic_scholar.py  seed resolution + recommendations
  rank.py                      batched Groq / open-weight LLM ranking
  zotero.py                    push picks, auto-group by month & subtopic
  store.py                     seen-ID dedupe
  notify.py                    digest formatting, SMTP
  feedback.py                  fold liked papers into seeds
  main.py                      digest / feedback entrypoints
data/seen.json                 IDs already surfaced
interests.yaml                 your research profile
```

To adapt this agent to another field, replace `interests.yaml`.
