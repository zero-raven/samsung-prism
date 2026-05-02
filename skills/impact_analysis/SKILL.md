---
name: finsight-hypothesize
description: >
  The core intelligence skill. Takes a structured event, queries the knowledge graph
  for prior context, generates investigation hypotheses via LLM, executes investigations
  via API calls (Google News, yfinance, Finnhub), then synthesizes a full causal chain.
  REPLACES the original RAG approach with live hypothesis-driven investigation.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 3 — Hypothesis-Driven Impact Analysis

## When to Run
- After finsight-extract produces significant events in data/events/

## Workflow
1. Run `python C:\Users\Asus\OneDrive\Desktop\Prism\finsight/hypothesize.py`
2. For each unprocessed event in data/events/:
   a. Query knowledge graph for prior entity connections
   b. Call Gemini 70B to generate 4 investigation hypotheses
   c. Execute each investigation via targeted API calls (NOT free-text search)
   d. Call Gemini 70B to synthesize all evidence into a causal chain
3. Write the causal chain to data/analysis/

## Input / Output Contract

### INPUT
- `data/events/evt_<id>.yaml`         → Structured event from Skill 2
- `data/graph/knowledge_graph.json`    → Prior entity connections
- `config.yaml`                        → Model settings, investigation count

### OUTPUT
- `data/analysis/chain_<event_id>.yaml` → Full causal chain analysis
- `data/logs/hypothesize.log`           → Investigation log

### Causal Chain Output Format (chain_<event_id>.yaml)
```yaml
event_id: "evt_20260501_001"
event_summary: "RBI holds repo rate steady at 6.5%"
graph_context: "banking sector connected to RBI, HDFC Bank belongs_to banking..."
investigations:
  - type: "SECTOR_CHECK"
    target: "banking"
    query: "Indian banking sector interest rate sensitivity"
    results:
      news_headlines: ["...", "..."]
      market_data: {sector_change: "+0.5%", volume: "above_average"}
  - type: "COMPANY_CHECK"
    target: "HDFC Bank"
    results:
      current_price: 1680.50
      change_pct: +0.8
      recent_news: ["..."]
  - type: "CORROBORATION"
    ...
  - type: "MACRO_CONTEXT"
    ...
causal_chain:
  trigger: "RBI maintained repo rate at 6.5%, signaling stable monetary policy"
  mechanism: "Stable rates benefit banking margins and support lending growth"
  affected_sectors:
    - sector: "banking"
      direction: "positive"
      magnitude: "medium"
      reasoning: "Banks benefit from rate stability..."
  time_horizon: "short_term"
  confidence: "HIGH"
  key_risks:
    - "Inflation data surprises could force rate action"
analyzed_at: "2026-05-01T10:10:00"
```

## Rules
- Use Gemini 2.0 Flash for BOTH hypothesis generation and synthesis
- Each investigation hypothesis MUST map to a concrete API call — no free-text search
- Investigation types: SECTOR_CHECK, COMPANY_CHECK, CORROBORATION, MACRO_CONTEXT
- Maximum 4 investigations per event to conserve API budget
- Skip events already analyzed (check if chain_<id>.yaml exists)
