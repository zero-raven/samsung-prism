---
name: prediction_engine
description: "Synthesizes the Causal Chain, Portfolio Impact, and Knowledge Graph to generate a directional trading signal."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 5: Prediction & Signal Generation

## Execution Trigger
- Run `python signal_gen.py` after `impact_<id>.yaml` is generated.

## Input / Output Contract
- **INPUT 1:** `data/analysis/chain_<id>.yaml`
- **INPUT 2:** `data/analysis/impact_<id>.yaml`
- **INPUT 3:** `data/graph/knowledge_graph.json`
- **OUTPUT:** `data/analysis/signal_<id>.yaml`

### Signal Output YAML Schema Example
```yaml
event_id: "evt_20260502_001"
signal:
  direction: "BULLISH"
  confidence: "MEDIUM"
  horizon: "medium_term"
  reasoning: "Tata manufacturing expansion highly correlates with Indian industrial growth."
  risk_flags: ["Tata fails to meet Apple production standards."]
```

## Strict Rules for LLM
1. **Graph Injection:** You MUST query the `knowledge_graph.json` for 2nd-degree connections (e.g., suppliers, partners) and inject this context into your reasoning.
2. **No Financial Advice:** Never use the words "BUY" or "SELL". Only use "BULLISH", "BEARISH", or "NEUTRAL".
3. **Pessimistic Confidence:** If the historical analogues contradict each other, you MUST default `confidence` to "LOW".
