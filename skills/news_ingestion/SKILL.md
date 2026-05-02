---
name: news_ingestion
description: "Fetches live news from external APIs and deduplicates them using SHA-256 hashing to prevent redundant processing."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 1: News Ingestion & Deduplication

## Execution Trigger
- Run continuously or manually via `python ingest.py`.

## Input / Output Contract
- **INPUT:** Live API data (Finnhub, GDELT, RSS).
- **OUTPUT:** `data/queue/pending_articles.yaml`

### Output YAML Schema Example
```yaml
articles:
  - headline: "Fed cuts rates by 50 bps"
    source: "Reuters"
    url: "https://..."
    published: "2026-05-02T10:00:00"
```

## Strict Rules for LLM
1. **Deduplication is Mandatory:** You must hash the headline and URL (SHA-256). Do not append an article if its hash already exists in the local cache.
2. **Format:** Output must be strictly valid YAML. Do not use Markdown blocks in the final file write.
