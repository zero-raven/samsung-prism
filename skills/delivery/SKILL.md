---
name: finsight-deliver
description: >
  Handles all user-facing output. Formats analysis results into clean Telegram messages,
  routes alerts by confidence level, handles portfolio commands, on-demand queries,
  and generates knowledge graph visualizations. The user's only interface to FinSight.
metadata:
  openclaw:
    requires:
      bins: ["python"]
---

# FinSight Skill 6 — Alert Delivery & Conversational Interface

## When to Run
- After finsight-signal produces a signal (proactive alert mode)
- When user sends a Telegram message (on-demand query mode)
- At briefing_time for morning briefing (scheduled mode)

## Input / Output Contract

### INPUT (Proactive Alert)
- `data/analysis/chain_<event_id>.yaml`    → Causal chain
- `data/analysis/impact_<event_id>.yaml`   → Portfolio impact
- `data/analysis/signal_<event_id>.yaml`   → Trading signal
- `data/graph/knowledge_graph.json`        → For visualization

### INPUT (On-Demand Query)
- User's Telegram message text
- Triggers a fresh pipeline run: extract → hypothesize → portfolio → signal

### INPUT (Commands)
- `/portfolio show` — Display current portfolio
- `/portfolio add TICKER QUANTITY PRICE` — Add holding
- `/portfolio remove TICKER` — Remove holding
- `/graph` — Send knowledge graph visualization
- `/status` — System health and stats

### OUTPUT
- Formatted Telegram message with:
  - 📰 What happened (trigger)
  - 📊 Market impact (mechanism + affected sectors)
  - 💼 Portfolio exposure (% affected, specific holdings)
  - 📈 Signal (direction + confidence + horizon)
  - 🔗 Reasoning chain (compressed)
  - ⚠️ Risk flags
- `data/briefing/queue.yaml` — Events queued for morning briefing
- `data/visualizations/graph.html` — Knowledge graph visualization
- `data/logs/deliver.log` — Delivery log

## Confidence Routing
- **HIGH confidence** → Immediate Telegram alert
- **MEDIUM confidence** → Queued for morning briefing
- **LOW confidence** → Logged only, not surfaced to user
