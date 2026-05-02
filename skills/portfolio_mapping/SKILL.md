---
name: finsight-portfolio
description: >
  Maps causal chain sector impacts to the user's specific portfolio holdings.
  Queries yfinance for current prices of affected NSE/BSE tickers and calculates
  directional exposure scores. Handles dynamic portfolio management via Telegram commands.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 4 — Portfolio Impact Mapping

## When to Run
- After finsight-hypothesize produces a causal chain in data/analysis/

## Workflow
1. Run `python C:\Users\Asus\OneDrive\Desktop\Prism\finsight/portfolio.py`
2. Reads the user's portfolio from data/portfolio/holdings.yaml
3. Reads causal chains from data/analysis/chain_*.yaml
4. Maps affected sectors to portfolio holdings
5. Queries yfinance for current prices
6. Calculates exposure score per holding
7. Writes portfolio impact report

## Input / Output Contract

### INPUT
- `data/portfolio/holdings.yaml`           → User's current portfolio
- `data/analysis/chain_<event_id>.yaml`    → Causal chains from Skill 3

### OUTPUT
- `data/analysis/impact_<event_id>.yaml`   → Portfolio-specific impact report
- `data/logs/portfolio.log`                → Processing log

### Portfolio Format (holdings.yaml)
```yaml
holdings:
  - ticker: "RELIANCE.NS"
    name: "Reliance Industries"
    sector: "energy"
    quantity: 10
    avg_cost: 2450.0
```

### Impact Output Format (impact_<event_id>.yaml)
```yaml
event_id: "evt_20260501_001"
portfolio_exposure:
  total_portfolio_value: 250000.0
  affected_value: 50000.0
  exposure_pct: 20.0
  direction: "negative"
affected_holdings:
  - ticker: "RELIANCE.NS"
    name: "Reliance Industries"
    current_price: 2480.0
    quantity: 10
    holding_value: 24800.0
    pct_of_portfolio: 9.9
    impact_direction: "negative"
    impact_magnitude: "medium"
unaffected_holdings_count: 3
```

## Rules
- Never make buy/sell recommendations — this is decision SUPPORT only
- If portfolio file doesn't exist, initialize from config defaults
- If yfinance fails for a ticker, use avg_cost as fallback price
