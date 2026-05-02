"""
FinSight Skill 5 — LLM-Native Signal Generation
==================================================
Generates directional signals by synthesizing causal chain + portfolio exposure.

═══════════════════════════════════════════════════════
INPUT:
    - data/analysis/chain_<event_id>.yaml    → Causal chain from Skill 3
    - data/analysis/impact_<event_id>.yaml   → Portfolio impact from Skill 4

OUTPUT:
    - data/analysis/signal_<event_id>.yaml   → Directional signal + reasoning
    - data/logs/signal.log                   → Processing log

TRIGGERS:
    - After Skill 4 (finsight-portfolio) writes impact reports
    - Can be run manually: python signal.py
═══════════════════════════════════════════════════════
"""

import sys
import os
import glob
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config_loader import (
    load_config, get_workspace_path, read_yaml, write_yaml, append_to_log
)
from shared.llm_client import generate_yaml


SIGNAL_PROMPT = """You are a financial signal generator for Indian retail investors (NSE/BSE market).
You do NOT give buy/sell recommendations. You generate a directional signal with confidence level.

EVENT: {event_summary}

CAUSAL CHAIN:
  Trigger: {trigger}
  Mechanism: {mechanism}
  Time Horizon: {time_horizon}
  Chain Confidence: {chain_confidence}
  Key Risks: {key_risks}

PORTFOLIO EXPOSURE:
  Total Portfolio Value: ₹{total_value}
  Affected Value: ₹{affected_value} ({exposure_pct}% of portfolio)
  Direction: {portfolio_direction}
  Affected Holdings:
{affected_holdings_text}

Generate a trading signal. Return ONLY valid YAML:

signal:
  direction: "BULLISH or BEARISH or NEUTRAL"
  confidence: "HIGH or MEDIUM or LOW"
  horizon: "days or weeks or months"
  affected_holdings:
    - ticker: "TICKER.NS"
      exposure_pct: 0.0
      expected_impact: "positive/negative, estimated range like +2% to +5%"
  reasoning: "2-3 sentences explaining the signal. Reference specific evidence."
  risk_flags:
    - "Specific factor that would invalidate this signal"
    - "Another risk"
  action_insight: "One sentence: what a retail investor should be AWARE of (not what they should do)"

RULES:
- NEVER say "buy" or "sell" — only indicate direction and awareness
- If evidence is mixed or insufficient, set confidence to LOW and direction to NEUTRAL
- The risk_flags must be specific and actionable, not generic
- Expected impact ranges should be realistic (not ±50% for routine news)
"""


def generate_signal(chain: dict, impact: dict, config: dict) -> dict:
    """
    Generate a directional signal from causal chain + portfolio impact.

    INPUT:
        chain  — Causal chain analysis dict from Skill 3
        impact — Portfolio impact report dict from Skill 4
        config — Full config dict

    OUTPUT:
        dict — Signal with direction, confidence, reasoning, risk flags
    """
    event_id = chain.get("event_id", "unknown")
    causal = chain.get("causal_chain", {})
    exposure = impact.get("portfolio_exposure", {})
    affected = impact.get("affected_holdings", [])
    model = config.get("llm", {}).get("reasoning_model", "gemini-2.0-flash")

    # Format affected holdings for prompt
    holdings_text = ""
    for h in affected:
        holdings_text += (
            f"    - {h.get('name', h.get('ticker'))}: "
            f"₹{h.get('holding_value', 0):,.2f} ({h.get('pct_of_portfolio', 0)}% of portfolio), "
            f"direction: {h.get('impact_direction', 'unknown')}, "
            f"magnitude: {h.get('impact_magnitude', 'unknown')}\n"
        )
    if not holdings_text:
        holdings_text = "    No holdings directly affected.\n"

    prompt = SIGNAL_PROMPT.format(
        event_summary=chain.get("event_summary", ""),
        trigger=causal.get("trigger", "Unknown event"),
        mechanism=causal.get("mechanism", "Unknown mechanism"),
        time_horizon=causal.get("time_horizon", "unknown"),
        chain_confidence=causal.get("confidence", "LOW"),
        key_risks=", ".join(causal.get("key_risks", ["None identified"])),
        total_value=exposure.get("total_portfolio_value", 0),
        affected_value=exposure.get("affected_value", 0),
        exposure_pct=exposure.get("exposure_pct", 0),
        portfolio_direction=exposure.get("direction", "neutral"),
        affected_holdings_text=holdings_text,
    )

    result = generate_yaml(prompt, model_name=model)
    signal = result.get("signal", result)

    # Build output
    output = {
        "event_id": event_id,
        "event_summary": chain.get("event_summary", ""),
        "signal": signal,
        "portfolio_exposure_pct": exposure.get("exposure_pct", 0),
        "generated_at": datetime.datetime.now().isoformat(),
        "model_used": model,
    }

    return output


def run_signal_generation():
    """
    Process all events that have impact reports but no signals.

    STEP 1: Find impact reports without matching signal files
    STEP 2: Load chain + impact for each
    STEP 3: Generate signal via LLM
    STEP 4: Write signal to data/analysis/
    """
    print("=" * 60)
    print("[Skill 5] FinSight Signal Generation Starting...")
    print("=" * 60)

    config = load_config()
    analysis_dir = get_workspace_path("analysis")

    # Find unprocessed impact reports
    impact_files = sorted(glob.glob(os.path.join(analysis_dir, "impact_evt_*.yaml")))
    if not impact_files:
        print("[Skill 5] No impact reports to process.")
        return []

    unprocessed = []
    for imf in impact_files:
        event_id = os.path.basename(imf).replace("impact_", "").replace(".yaml", "")
        signal_path = os.path.join(analysis_dir, f"signal_{event_id}.yaml")
        if not os.path.exists(signal_path):
            unprocessed.append((imf, event_id))

    if not unprocessed:
        print("[Skill 5] All impact reports already have signals.")
        return []

    print(f"[Skill 5] Generating signals for {len(unprocessed)} events...")
    signals = []

    for imf, event_id in unprocessed:
        impact = read_yaml(imf)
        chain_path = os.path.join(analysis_dir, f"chain_{event_id}.yaml")
        chain = read_yaml(chain_path)

        if not chain:
            print(f"  ⚠ No chain found for {event_id}. Skipping.")
            continue

        summary = chain.get("event_summary", "Unknown")
        print(f"\n[Skill 5] Generating signal: {summary[:60]}...")

        try:
            signal = generate_signal(chain, impact, config)
            signal_path = get_workspace_path("analysis", f"signal_{event_id}.yaml")
            write_yaml(signal_path, signal)
            signals.append(signal)

            direction = signal.get("signal", {}).get("direction", "UNKNOWN")
            confidence = signal.get("signal", {}).get("confidence", "UNKNOWN")
            print(f"  ✓ Signal: {direction} ({confidence})")

            append_to_log(
                f"Signal for {event_id}: {direction} ({confidence}) | {summary[:60]}",
                "signal.log"
            )
        except Exception as e:
            print(f"  ✗ Signal generation failed: {e}")
            append_to_log(f"FAILED signal for {event_id}: {e}", "signal.log")

    print(f"\n[Skill 5] Done. Generated {len(signals)} signals.")
    return signals


if __name__ == "__main__":
    from shared.config_loader import ensure_workspace
    ensure_workspace()
    run_signal_generation()
