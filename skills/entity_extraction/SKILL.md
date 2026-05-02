---
name: finsight-extract
description: >
  Takes raw articles from the ingestion queue and extracts structured entities
  (companies, sectors, countries, commodities) using Gemini LLM. Updates the
  knowledge graph with discovered entities and relationships.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 2 — Entity Extraction & Structuring

## When to Run
- After finsight-ingest completes and pending_articles.yaml has new articles

## Workflow
1. Run `python C:\Users\Asus\OneDrive\Desktop\Prism\finsight/extract.py`
2. The script reads each pending article
3. Calls Gemini (2.0 Flash) for structured entity extraction
4. Writes significant events to data/events/
5. Updates the knowledge graph with new entities and relationships
6. Clears the pending queue

## Input / Output Contract

### INPUT
- `data/queue/pending_articles.yaml` — articles from Skill 1

### OUTPUT
- `data/events/evt_<id>.yaml` — one file per significant event (significance ≥ 5)
- `data/graph/knowledge_graph.json` — updated knowledge graph
- `data/logs/extract.log` — extraction log
- `data/queue/pending_articles.yaml` — cleared after processing

### Event Output Format (evt_<id>.yaml)
```yaml
event_id: "evt_20260501_001"
source_article:
  headline: "RBI holds repo rate steady at 6.5%"
  source: "google_news"
  url: "https://..."
  published: "2026-05-01T10:00:00"
entities:
  companies: ["HDFC Bank", "SBI", "ICICI Bank"]
  sectors: ["banking"]
  countries: ["India"]
  commodities: []
event_type: "central_bank"
significance: 7
one_line_summary: "RBI maintains repo rate, signaling stable monetary policy"
extracted_at: "2026-05-01T10:05:00"
```

## Rules
- Use Gemini 2.0 Flash for extraction (fast, cheap)
- Only write events with significance ≥ 5 to data/events/
- Log all low-significance events to data/logs/low_significance.log
- Always update the knowledge graph even for low-significance events
