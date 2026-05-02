---
name: entity_extraction
description: "Parses raw articles, extracts entities (companies, sectors), assigns a significance score, and updates the Knowledge Graph."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 2: Entity Extraction & Structuring

## Execution Trigger
- Run `python extract.py` after `news_ingestion` updates the queue.

## Input / Output Contract
- **INPUT:** `data/queue/pending_articles.yaml`
- **OUTPUT 1:** `data/events/evt_<id>.yaml` (Only for events with significance >= 5)
- **OUTPUT 2:** `data/graph/knowledge_graph.json` (Always updated)

### Event Output YAML Schema Example
```yaml
event_id: "evt_20260502_001"
source_article:
  headline: "Apple shifts production to Tata"
entities:
  companies: ["Apple", "Tata"]
  sectors: ["technology", "manufacturing"]
event_type: "corporate_action"
significance: 7
```

## Strict Rules for LLM
1. **Filtering:** If the `significance` score is less than 5, DO NOT write an `evt_<id>.yaml` file. Just log it.
2. **Graph Maintenance:** You must update `knowledge_graph.json` with the extracted entities regardless of the significance score.
3. **Format:** Output must be strictly valid YAML. Do not include markdown code fences in the file contents.
