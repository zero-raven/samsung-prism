---
name: finsight-ingest
description: >
  Fetches financial news from Google News RSS (Indian markets), GDELT (global geopolitics),
  and Finnhub (global markets). Deduplicates articles and writes a queue for extraction.
  Runs on every heartbeat. No LLM calls — pure data fetching.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 1 — News Ingestion & Deduplication

## When to Run
- On every heartbeat cycle
- This is always the FIRST skill in the pipeline

## Workflow
1. Run `python C:\Users\Asus\OneDrive\Desktop\Prism\finsight/ingest.py`
2. The script fetches news from configured sources (Google News RSS, GDELT, Finnhub)
3. It deduplicates by headline similarity
4. It writes new articles to the pending queue

## Input / Output Contract

### INPUT
- `config.yaml` — news source configuration (queries, regions, limits)
- `data/queue/seen_hashes.txt` — previously seen article hashes (for dedup)

### OUTPUT
- `data/queue/pending_articles.yaml` — list of new, deduplicated articles
- `data/queue/seen_hashes.txt` — updated with new hashes
- `data/logs/ingest.log` — timestamped log of ingestion results

### Output Format (pending_articles.yaml)
```yaml
articles:
  - id: "art_20260501_001"
    headline: "RBI holds repo rate steady at 6.5%"
    summary: "The Reserve Bank of India..."
    source: "google_news"
    url: "https://..."
    published: "2026-05-01T10:00:00"
    topic: "central_bank"
  - id: "art_20260501_002"
    ...
```

## Rules
- Never call any LLM — this is pure data fetching
- If all sources fail, log the error and write an empty queue
- If the queue already has pending articles, APPEND to it (don't overwrite)
- Respect rate limits: max 60 Finnhub calls/minute
