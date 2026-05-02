"""
FinSight Pipeline Orchestrator
================================
Runs the full 6-skill pipeline in sequence.
This is the main entry point — called by OpenClaw heartbeat or manually.

═══════════════════════════════════════════════════════
PIPELINE FLOW:

  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
  │  Skill 1     │────▶│  Skill 2     │────▶│  Skill 3         │
  │  INGEST      │     │  EXTRACT     │     │  HYPOTHESIZE     │
  │              │     │              │     │                  │
  │ IN: RSS/APIs │     │ IN: queue    │     │ IN: events+graph │
  │ OUT: queue   │     │ OUT: events  │     │ OUT: causal chain│
  └──────────────┘     │      +graph  │     └────────┬─────────┘
                       └──────────────┘              │
                                                     ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
  │  Skill 6     │◀────│  Skill 5     │◀────│  Skill 4         │
  │  DELIVER     │     │  SIGNAL      │     │  PORTFOLIO       │
  │              │     │              │     │                  │
  │ IN: all data │     │ IN: chain    │     │ IN: chain+       │
  │ OUT: Telegram│     │    +impact   │     │     holdings     │
  │     messages │     │ OUT: signal  │     │ OUT: impact      │
  └──────────────┘     └──────────────┘     └──────────────────┘

USAGE:
    python pipeline.py              # Run full pipeline
    python pipeline.py --skill 1    # Run only Skill 1
    python pipeline.py --skill 3    # Run only Skill 3 (on existing events)
═══════════════════════════════════════════════════════
"""

import sys
import os
import datetime
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.config_loader import ensure_workspace, append_to_log


def run_full_pipeline():
    """Execute the complete FinSight pipeline: Skills 1 → 2 → 3 → 4 → 5 → 6"""

    print("============================================================")
    print("            FinSight Pipeline - Full Run                    ")
    print(f"            {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST'):<36}    ")
    print("============================================================\n")

    ensure_workspace()
    start_time = datetime.datetime.now()

    # ── Skill 1: Ingest ──
    print("\n" + ">" * 20 + " SKILL 1: INGEST " + "<" * 20)
    try:
        from ingest import run_ingestion
        new_articles = run_ingestion()
        article_count = len(new_articles) if new_articles else 0
        print(f"\n[OK] Skill 1 complete: {article_count} new articles")
    except Exception as e:
        print(f"\n[ERROR] Skill 1 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 1: {e}", "pipeline.log")
        article_count = 0

    if article_count == 0:
        print("\n[PAUSE] No new articles. Pipeline complete (HEARTBEAT_OK).")
        append_to_log("HEARTBEAT_OK — No new articles.", "pipeline.log")
        return

    # ── Skill 2: Extract ──
    print("\n" + ">" * 20 + " SKILL 2: EXTRACT " + "<" * 20)
    try:
        from extract import run_extraction
        events = run_extraction()
        event_count = len(events) if events else 0
        print(f"\n[OK] Skill 2 complete: {event_count} significant events")
    except Exception as e:
        print(f"\n[ERROR] Skill 2 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 2: {e}", "pipeline.log")
        return

    if event_count == 0:
        print("\n[PAUSE] No significant events. Pipeline complete (HEARTBEAT_OK).")
        append_to_log("HEARTBEAT_OK — No significant events.", "pipeline.log")
        return

    # ── Skill 3: Impact Analysis (RAG) ──
    print("\n" + ">" * 20 + " SKILL 3: IMPACT ANALYSIS " + "<" * 20)
    try:
        from analyze import run_impact_analysis
        analyses = run_impact_analysis()
        analysis_count = len(analyses) if analyses else 0
        print(f"\n[OK] Skill 3 complete: {analysis_count} causal chains")
    except Exception as e:
        print(f"\n[ERROR] Skill 3 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 3: {e}", "pipeline.log")
        return

    # ── Skill 4: Portfolio ──
    print("\n" + ">" * 20 + " SKILL 4: PORTFOLIO " + "<" * 20)
    try:
        from portfolio import run_portfolio_mapping
        impacts = run_portfolio_mapping()
        impact_count = len(impacts) if impacts else 0
        print(f"\n[OK] Skill 4 complete: {impact_count} portfolio impacts")
    except Exception as e:
        print(f"\n[ERROR] Skill 4 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 4: {e}", "pipeline.log")

    # ── Skill 5: Signal ──
    print("\n" + ">" * 20 + " SKILL 5: SIGNAL " + "<" * 20)
    try:
        from signal_gen import run_signal_generation
        signals = run_signal_generation()
        signal_count = len(signals) if signals else 0
        print(f"\n[OK] Skill 5 complete: {signal_count} signals generated")
    except Exception as e:
        print(f"\n[ERROR] Skill 5 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 5: {e}", "pipeline.log")

    # ── Skill 6: Deliver ──
    print("\n" + ">" * 20 + " SKILL 6: DELIVER " + "<" * 20)
    try:
        from deliver import route_and_deliver
        deliveries = route_and_deliver()
        delivery_count = len(deliveries) if deliveries else 0
        print(f"\n[OK] Skill 6 complete: {delivery_count} deliveries routed")
    except Exception as e:
        print(f"\n[ERROR] Skill 6 failed: {e}")
        append_to_log(f"PIPELINE FAILED at Skill 6: {e}", "pipeline.log")

    # ── Summary ──
    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    summary = (
        f"Pipeline complete in {elapsed:.1f}s. "
        f"Articles: {article_count}, Events: {event_count}, "
        f"Analyses: {analysis_count}, Deliveries: {delivery_count}"
    )
    print(f"\n{'=' * 60}")
    print(f"[OK] {summary}")
    print(f"{'=' * 60}")
    append_to_log(summary, "pipeline.log")


def run_single_skill(skill_num: int):
    """Run a single skill by number."""
    ensure_workspace()

    skill_map = {
        1: ("INGEST", "ingest", "run_ingestion"),
        2: ("EXTRACT", "extract", "run_extraction"),
        3: ("ANALYZE", "analyze", "run_impact_analysis"),
        4: ("PORTFOLIO", "portfolio", "run_portfolio_mapping"),
        5: ("SIGNAL", "signal_gen", "run_signal_generation"),
        6: ("DELIVER", "deliver", "route_and_deliver"),
    }

    if skill_num not in skill_map:
        print(f"Invalid skill number: {skill_num}. Use 1-6.")
        return

    name, module, func_name = skill_map[skill_num]
    print(f"\n> Running Skill {skill_num}: {name}")

    try:
        mod = __import__(module)
        func = getattr(mod, func_name)
        result = func()
        print(f"\n[OK] Skill {skill_num} ({name}) complete.")
        return result
    except Exception as e:
        print(f"\n[ERROR] Skill {skill_num} ({name}) failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight Pipeline Orchestrator")
    parser.add_argument("--skill", type=int, help="Run only a specific skill (1-6)")
    args = parser.parse_args()

    if args.skill:
        run_single_skill(args.skill)
    else:
        run_full_pipeline()
