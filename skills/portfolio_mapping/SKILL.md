---
name: portfolio_mapping
description: "Maps the affected sectors from the Causal Chain to the user's specific holdings to calculate financial exposure."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 4: Portfolio Mapping

## Execution Trigger
- Run `python portfolio.py` after a new `chain_<id>.yaml` is created.

## Input / Output Contract
- **INPUT 1:** `data/analysis/chain_<id>.yaml`
- **INPUT 2:** `config/portfolio.yaml` (User's actual holdings)
- **OUTPUT:** `data/analysis/impact_<id>.yaml`

### Impact Report Output YAML Schema Example
```yaml
event_id: "evt_20260502_001"
portfolio_exposure:
  total_portfolio_value: 15000.00
  affected_value: 3000.00
  exposure_pct: 20.0
  direction: "positive"
affected_holdings:
  - ticker: "AAPL"
    sector: "technology"
    holding_value: 3000.00
```

## Strict Rules for LLM
1. **Live Pricing:** You must fetch live market prices (via `yfinance` or equivalent) to calculate accurate `total_portfolio_value`.
2. **Exact Matching:** Only flag a holding if its `sector` exactly matches one of the `affected_sectors` from the causal chain. No fuzzy matching allowed.
