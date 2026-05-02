"""
FinSight Skill 6 — Alert Delivery & Conversational Interface
===============================================================
Formats and delivers analysis results. Routes by confidence.
Handles user commands and on-demand queries.

═══════════════════════════════════════════════════════
INPUT:
    - data/analysis/signal_<event_id>.yaml   → Signal from Skill 5
    - data/analysis/chain_<event_id>.yaml    → Causal chain from Skill 3
    - data/analysis/impact_<event_id>.yaml   → Portfolio impact from Skill 4
    - data/graph/knowledge_graph.json        → For graph visualization

OUTPUT:
    - Formatted alert text (returned as string for OpenClaw to send via Telegram)
    - data/briefing/queue.yaml               → Events queued for morning briefing
    - data/visualizations/graph.html         → Interactive graph visualization
    - data/logs/deliver.log                  → Delivery log

TRIGGERS:
    - After Skill 5 generates signals (proactive)
    - User Telegram message (on-demand)
    - Cron schedule for morning briefing
    - Manual: python deliver.py
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
from shared.graph_manager import GraphManager


# ═══════════════════════════════════════════════════════════
# MESSAGE FORMATTING
# ═══════════════════════════════════════════════════════════

def format_alert_message(chain: dict, impact: dict, signal_data: dict) -> str:
    """
    Format a full analysis into a clean, readable alert message.

    INPUT:
        chain       — Causal chain analysis from Skill 3
        impact      — Portfolio impact report from Skill 4
        signal_data — Signal from Skill 5

    OUTPUT:
        str — Formatted message ready for Telegram delivery
    """
    causal = chain.get("causal_chain", {})
    exposure = impact.get("portfolio_exposure", {})
    signal = signal_data.get("signal", {})

    # Direction emoji
    dir_emoji = {
        "BULLISH": "📈",
        "BEARISH": "📉",
        "NEUTRAL": "➡️",
    }
    conf_emoji = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }

    direction = signal.get("direction", "NEUTRAL")
    confidence = signal.get("confidence", "LOW")
    horizon = signal.get("horizon", "unknown")

    msg = []
    msg.append("═══════════════════════════════")
    msg.append("🔔 *FinSight Alert*")
    msg.append("═══════════════════════════════")

    # What happened
    msg.append(f"\n📰 *What happened:*")
    msg.append(f"   {causal.get('trigger', 'Unknown event')}")

    # Market impact
    msg.append(f"\n📊 *Market Impact:*")
    msg.append(f"   {causal.get('mechanism', 'Analysis pending...')}")

    # Affected sectors
    affected_sectors = causal.get("affected_sectors", [])
    if affected_sectors:
        msg.append(f"\n🏭 *Affected Sectors:*")
        for s in affected_sectors:
            s_dir = "↑" if s.get("direction") == "positive" else "↓" if s.get("direction") == "negative" else "→"
            msg.append(f"   {s_dir} {s.get('sector', 'Unknown')}: {s.get('direction', 'neutral')} ({s.get('magnitude', 'low')})")

    # Portfolio exposure
    msg.append(f"\n💼 *Your Portfolio Exposure:*")
    msg.append(f"   Total value: ₹{exposure.get('total_portfolio_value', 0):,.2f}")
    msg.append(f"   Affected: ₹{exposure.get('affected_value', 0):,.2f} ({exposure.get('exposure_pct', 0)}%)")
    msg.append(f"   Direction: {exposure.get('direction', 'neutral')}")

    # Affected holdings detail
    affected_holdings = impact.get("affected_holdings", [])
    if affected_holdings:
        msg.append(f"\n📋 *Affected Holdings:*")
        for h in affected_holdings[:5]:
            h_dir = "↑" if h.get("impact_direction") == "positive" else "↓"
            msg.append(f"   {h_dir} {h.get('name', h.get('ticker'))}: ₹{h.get('current_price', 0):,.2f} ({h.get('pct_of_portfolio', 0)}% of portfolio)")

    # Signal
    msg.append(f"\n{dir_emoji.get(direction, '➡️')} *Signal:* {direction} | {conf_emoji.get(confidence, '🟢')} Confidence: {confidence} | ⏱ Horizon: {horizon}")

    # Reasoning
    reasoning = signal.get("reasoning", causal.get("summary_for_investor", ""))
    if reasoning:
        msg.append(f"\n🔗 *Reasoning:*")
        msg.append(f"   {reasoning}")

    # Action insight
    insight = signal.get("action_insight", "")
    if insight:
        msg.append(f"\n💡 *Insight:* {insight}")

    # Risk flags
    risks = signal.get("risk_flags", causal.get("key_risks", []))
    if risks:
        msg.append(f"\n⚠️ *Risk Flags:*")
        for r in risks[:3]:
            msg.append(f"   • {r}")

    msg.append("\n═══════════════════════════════")
    msg.append(f"🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    msg.append("_FinSight — Decision Support Only_")

    return "\n".join(msg)


def format_briefing(events: list) -> str:
    """
    Format multiple events into a morning briefing message.

    INPUT:
        events — list of (chain, impact, signal) tuples

    OUTPUT:
        str — Formatted morning briefing message
    """
    msg = []
    msg.append("═══════════════════════════════")
    msg.append("☀️ *FinSight Morning Briefing*")
    msg.append(f"📅 {datetime.datetime.now().strftime('%A, %B %d, %Y')}")
    msg.append("═══════════════════════════════")

    # Sort by portfolio exposure (highest impact first)
    events.sort(key=lambda e: e[1].get("portfolio_exposure", {}).get("exposure_pct", 0), reverse=True)

    for i, (chain, impact, signal_data) in enumerate(events[:4], 1):
        causal = chain.get("causal_chain", {})
        signal = signal_data.get("signal", {})
        exposure = impact.get("portfolio_exposure", {})

        direction = signal.get("direction", "NEUTRAL")
        dir_emoji = "📈" if direction == "BULLISH" else "📉" if direction == "BEARISH" else "➡️"

        msg.append(f"\n*{i}. {causal.get('trigger', 'Event')}*")
        msg.append(f"   {dir_emoji} {direction} | Exposure: {exposure.get('exposure_pct', 0)}%")
        msg.append(f"   {signal.get('reasoning', '')[:150]}")

    msg.append("\n═══════════════════════════════")
    msg.append("_Reply with any event number for full analysis_")

    return "\n".join(msg)


# ═══════════════════════════════════════════════════════════
# CONFIDENCE ROUTING
# ═══════════════════════════════════════════════════════════

def route_and_deliver():
    """
    Route undelivered signals by confidence level.

    STEP 1: Find signal files not yet delivered
    STEP 2: For each, load chain + impact + signal
    STEP 3: Route: HIGH → immediate, MEDIUM → briefing queue, LOW → log only
    STEP 4: Return formatted messages for OpenClaw to send

    OUTPUT:
        list of dicts: [{type: "immediate"|"briefing"|"log", message: str, event_id: str}]
    """
    print("=" * 60)
    print("[Skill 6] FinSight Delivery & Routing Starting...")
    print("=" * 60)

    config = load_config()
    analysis_dir = get_workspace_path("analysis")

    signal_files = sorted(glob.glob(os.path.join(analysis_dir, "signal_evt_*.yaml")))
    if not signal_files:
        print("[Skill 6] No signals to deliver.")
        return []

    # Track delivered signals
    delivered_path = get_workspace_path("logs", "delivered.txt")
    delivered_ids = set()
    if os.path.exists(delivered_path):
        with open(delivered_path, "r") as f:
            delivered_ids = set(line.strip() for line in f)

    deliveries = []
    briefing_queue = []

    for sf in signal_files:
        event_id = os.path.basename(sf).replace("signal_", "").replace(".yaml", "")

        if event_id in delivered_ids:
            continue

        signal_data = read_yaml(sf)
        chain = read_yaml(os.path.join(analysis_dir, f"chain_{event_id}.yaml"))
        impact = read_yaml(os.path.join(analysis_dir, f"impact_{event_id}.yaml"))

        if not chain or not signal_data:
            continue

        confidence = signal_data.get("signal", {}).get("confidence", "LOW")
        summary = chain.get("event_summary", "Unknown")

        if confidence == "HIGH":
            message = format_alert_message(chain, impact, signal_data)
            deliveries.append({
                "type": "immediate",
                "message": message,
                "event_id": event_id,
                "confidence": confidence,
            })
            print(f"  🔴 HIGH: {summary[:60]} → Immediate alert")

        elif confidence == "MEDIUM":
            briefing_queue.append((chain, impact, signal_data))
            deliveries.append({
                "type": "briefing",
                "message": f"Queued for briefing: {summary[:60]}",
                "event_id": event_id,
                "confidence": confidence,
            })
            print(f"  🟡 MEDIUM: {summary[:60]} → Briefing queue")

        else:
            deliveries.append({
                "type": "log",
                "message": f"Logged (low confidence): {summary[:60]}",
                "event_id": event_id,
                "confidence": confidence,
            })
            print(f"  🟢 LOW: {summary[:60]} → Logged only")

        # Mark as delivered
        delivered_ids.add(event_id)
        append_to_log(f"DELIVERED ({confidence}): {event_id} | {summary[:60]}", "deliver.log")

    # Save delivered tracking
    with open(delivered_path, "w") as f:
        for did in delivered_ids:
            f.write(did + "\n")

    # Save briefing queue
    if briefing_queue:
        queue_path = get_workspace_path("briefing", "queue.yaml")
        existing = read_yaml(queue_path)
        existing_items = existing.get("items", [])
        for chain, impact, signal_data in briefing_queue:
            existing_items.append({
                "event_id": signal_data.get("event_id"),
                "event_summary": chain.get("event_summary"),
                "signal": signal_data.get("signal"),
                "exposure_pct": impact.get("portfolio_exposure", {}).get("exposure_pct", 0),
                "queued_at": datetime.datetime.now().isoformat(),
            })
        write_yaml(queue_path, {"items": existing_items})

    # Print immediate alerts
    immediate = [d for d in deliveries if d["type"] == "immediate"]
    if immediate:
        print(f"\n{'=' * 60}")
        print(f"[Skill 6] {len(immediate)} IMMEDIATE ALERT(S):")
        print(f"{'=' * 60}")
        for d in immediate:
            print(d["message"])
            print()

    summary = (
        f"Delivered: {len([d for d in deliveries if d['type'] == 'immediate'])} immediate, "
        f"{len([d for d in deliveries if d['type'] == 'briefing'])} queued, "
        f"{len([d for d in deliveries if d['type'] == 'log'])} logged"
    )
    print(f"\n[Skill 6] {summary}")

    return deliveries


def generate_graph_visualization() -> str:
    """
    Generate and return path to knowledge graph visualization.

    OUTPUT: str — Path to the generated HTML file, or status message
    """
    graph = GraphManager()
    stats = graph.get_stats()

    if stats["total_nodes"] == 0:
        return "Knowledge graph is empty. Run the pipeline first to populate it."

    html_path = graph.render_html()
    if html_path:
        return f"📊 Knowledge Graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges\nVisualization: {html_path}"
    return f"📊 Knowledge Graph Stats: {stats}"


def get_system_status() -> str:
    """
    Generate system status report.

    OUTPUT: str — Formatted status message
    """
    analysis_dir = get_workspace_path("analysis")
    events_dir = get_workspace_path("events")
    graph = GraphManager()
    stats = graph.get_stats()

    event_count = len(glob.glob(os.path.join(events_dir, "evt_*.yaml")))
    chain_count = len(glob.glob(os.path.join(analysis_dir, "chain_*.yaml")))
    signal_count = len(glob.glob(os.path.join(analysis_dir, "signal_*.yaml")))

    msg = [
        "⚙️ *FinSight System Status*",
        f"📰 Events tracked: {event_count}",
        f"🔍 Analyses completed: {chain_count}",
        f"📈 Signals generated: {signal_count}",
        f"🕸️ Knowledge Graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges",
        f"  • {stats.get('nodes_by_type', {})}",
        f"🕐 Last check: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M IST')}",
    ]
    return "\n".join(msg)


if __name__ == "__main__":
    from shared.config_loader import ensure_workspace
    ensure_workspace()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", action="store_true", help="Generate graph visualization")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--briefing", action="store_true", help="Generate morning briefing")
    args = parser.parse_args()

    if args.graph:
        print(generate_graph_visualization())
    elif args.status:
        print(get_system_status())
    elif args.briefing:
        # Load briefing queue and format
        queue_path = get_workspace_path("briefing", "queue.yaml")
        queue = read_yaml(queue_path)
        items = queue.get("items", [])
        if items:
            print(f"Morning briefing: {len(items)} queued events")
            # Would format and send via Telegram
        else:
            print("No events in briefing queue.")
    else:
        route_and_deliver()
