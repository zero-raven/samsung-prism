---
name: delivery
description: "Routes formatted markdown alerts to the user via Telegram based on signal confidence and portfolio exposure."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 6: Alert Delivery & Routing

## Execution Trigger
- Run `python deliver.py` as the final step of the pipeline.

## Input / Output Contract
- **INPUT:** `data/analysis/signal_<id>.yaml`
- **OUTPUT:** Markdown message sent via Telegram Bot API.

## Strict Rules for LLM
1. **Routing Logic (CRITICAL):**
   - **Immediate Alert:** Only send immediately if `confidence` == "HIGH" AND `exposure_pct` > 5%.
   - **Batching:** If `confidence` == "MEDIUM", do NOT send. Append it to the morning briefing queue.
   - **Silent:** If `confidence` == "LOW", do not send and do not batch.
2. **Formatting:** Telegram requires strict Markdown V2. Ensure all special characters are escaped correctly to prevent API failure.
