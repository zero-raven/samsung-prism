---
name: impact_analysis
description: "Uses Structured Hybrid RAG to find historical analogues and synthesizes a causal chain of market impact."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 3: Impact Analysis (RAG Engine)

## Execution Trigger
- Run `python analyze.py` when a new `evt_<id>.yaml` is created.

## Input / Output Contract
- **INPUT 1:** `data/events/evt_<id>.yaml` (Current Event)
- **INPUT 2:** `data/historical_events.yaml` (Golden Dataset via ChromaDB)
- **OUTPUT:** `data/analysis/chain_<id>.yaml`

### Causal Chain Output YAML Schema Example
```yaml
event_id: "evt_20260502_001"
causal_chain:
  trigger: "Apple shifts production."
  mechanism: "Tata gains massive revenue pipeline, Foxconn loses volume."
  affected_sectors:
    - sector: "manufacturing"
      direction: "mixed"
      magnitude: "high"
      reasoning: "Tata (Positive), Foxconn (Negative)."
  time_horizon: "medium_term"
```

## Strict Rules for LLM
1. **Metadata Filtering First:** Before performing vector similarity, you MUST filter ChromaDB using `where={"event_type": current_event_type}`.
2. **No Hallucination:** Base the `causal_chain` ONLY on the retrieved historical analogues. Do not invent impacts without historical precedent.
