# paper-agent

Daily reading recommendations for systems researchers. Pulls new papers from arXiv, Semantic Scholar recommendations, and tech-blog feeds; ranks them against an interest profile with the Claude API; emails a short digest; and files each pick into a Zotero collection ready to read.

## How it works

- `interests.yaml` is the brain: weighted keyword clusters, venues, seed papers, blog feeds, and daily limits. Edit this, not the code.
- `daily-digest` (12:00 UTC) fetches candidates, drops anything already seen, sends one batched ranking call to Claude, pushes the top picks to Zotero (tagged `agent-inbox`), and emails the digest with a per-pick note on why it matters to you.
- `weekly-feedback` (Sundays) reads papers you tagged `keep` in Zotero, folds them into `seed_papers`, and opens a PR so you approve changes to your own profile. Recommendations tighten as seeds accumulate.
- Feed failures appear in the digest instead of being swallowed.

## Setup

1. Zotero: create an API key with write access at zotero.org/settings/keys; note your userID from the same page. Optionally create an inbox collection and note its key (the 8-character code in its URL).
2. Add repository secrets: `ANTHROPIC_API_KEY`, `ZOTERO_API_KEY`, `ZOTERO_USER_ID`, `ZOTERO_COLLECTION` (optional), `S2_API_KEY` (optional, raises Semantic Scholar rate limits), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `NOTIFY_EMAIL`.
3. Adjust `interests.yaml` (clusters, feeds, `max_picks_per_day`) and trigger `daily-digest` manually once.

Rating workflow: tag a good paper `keep` in Zotero; delete duds. That is the entire feedback interface.

## Local run

```bash
pip install -r requirements.txt
python -m agent.main digest
python -m agent.main feedback
```

## Layout

```
agent/
  config.py                paths, interest loading
  sources/arxiv.py         new submissions by category
  sources/blogs.py         RSS/Atom tech blogs
  sources/semantic_scholar.py  seed resolution + recommendations
  rank.py                  batched Claude ranking
  zotero.py                push picks, read feedback tags
  store.py                 seen-ID dedupe
  notify.py                digest formatting, SMTP
  feedback.py              fold liked papers into seeds
  main.py                  digest / feedback entrypoints
data/seen.json             IDs already surfaced
interests.yaml             your research profile
```

To adapt this agent to another field, replace `interests.yaml`.
