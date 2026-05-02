---
name: finsight-signal
description: >
  Generates a directional trading signal (BULLISH/BEARISH/NEUTRAL) by synthesizing
  the causal chain from Skill 3 with the portfolio exposure from Skill 4. Uses LLM
  reasoning over the combined evidence — no statistical models or trained ML.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 5 — LLM-Native Signal Generation

## When to Run
- After finsight-portfolio produces an impact report

## Input / Output Contract

### INPUT
- `data/analysis/chain_<event_id>.yaml`    → Causal chain from Skill 3
- `data/analysis/impact_<event_id>.yaml`   → Portfolio impact from Skill 4

### OUTPUT
- `data/analysis/signal_<event_id>.yaml`   → Directional signal with reasoning
- `data/logs/signal.log`                   → Processing log

### Signal Output Format
```yaml
event_id: "evt_20260501_001"
signal:
  direction: "BEARISH"
  confidence: "HIGH"
  horizon: "short_term"
  affected_holdings:
    - ticker: "RELIANCE.NS"
      exposure_pct: 12.0
      expected_impact: "negative, -3% to -7%"
  reasoning: "2-3 sentence summary of why this signal was generated"
  risk_flags:
    - "Factor that could invalidate this signal"
```
